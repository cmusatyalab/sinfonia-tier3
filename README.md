# Sinfonia

Manages discovery of nearby cloudlets and deployment of backends for
edge-native applications.

The framework is a 3 tiered system. Tier 1 is located in the cloud and tracks
availability of the Tier 2 instances running on the edge of the network
(cloudlets) where backends can be deployed. Tier 3 is the client application
that mediates the discovery and deployment process for edge-native
applications.

This repository implements an example Tier3 client which can be used both as a
command-line application and as a Python library.


## Installation

You probably don't need to install this directly, most of the time it should
get installed as a dependency of whichever edge-native application is using
the Sinfonia framework to discover nearby cloudlets.

But if you want to run the standalone command-line application, you can install
this with installable with `pipx install sinfonia-tier3` or
`pip install [--user] sinfonia-tier3`.


## Usage

The `sinfonia-tier3` application would normally be called by any edge-native
application that uses the Sinfonia framework to deploy its application specific
backend on a nearby cloudlet.

The information needed by the application are the URL of a Tier1 instance
and the UUID identifying the required backend. The remainder of the arguments
consist of the actual frontend application and arguments that will be launched
in an seperate network namespace connecting back to the deployed backend.

    $ sinfonia-tier3 <tier1-url> <uuid> <frontend-app> <args...>

An example application with UUID:00000000-0000-0000-0000-000000000000 (or the
convenient alias 'helloworld') starts an nginx server that will be accessible
with the hostname 'helloworld'.

    $ sinfonia-tier3 https://tier1.server.url/ helloworld /bin/sh
    sinfonia$ curl -v http://helloworld/
    ...
    sinfonia$ exit

When the frontend application exits, the network namespace and WireGuard tunnel
are cleaned up. Any resources on the cloudlet will be automatically released
once the Sinfonia-tier2 instance notices the VPN tunnel has been idle.


## Installation from this source repository

You need a recent version of `poetry`

    $ pip install --user pipx
    $ ~/.local/bin/pipx ensurepath
    ... possibly restart shell to pick up the right PATH
    $ pipx install poetry

And then use poetry to install the necessary dependencies,

    $ git clone https://github.com/cmusatyalab/sinfonia-tier3.git
    $ cd sinfonia-tier3
    $ poetry install
    $ poetry run sinfonia-tier3 ...
    ... or
    $ poetry shell
    (env)$ sinfonia-tier3 ...


## Why do we need a sudo password when deploying

Actually you should not need a password if `wireguard4netns` works correctly
But if for some reason it fails to create the tuntap device and launch
wireguard-go, the code will fall back on the older `sudo` implementation.

The older `sudo` implementation uses the in-kernel Wireguard implementation and
needs root access to create and configure the WireGuard device and endpoint.
All of the code running as root is contained in
[src/sinfonia_tier3/root_helper.py](https://github.com/cmusatyalab/sinfonia-tier3/blob/main/src/sinfonia_tier3/root_helper.py)

It runs the equivalent of the following.

```sh
    ip link add wg-tunnel type wireguard
    wg set wg-tunnel private-key <private-key> peer <public-key> endpoint ...
    ip link set dev wg-tunnel netns <application network namespace>
```
