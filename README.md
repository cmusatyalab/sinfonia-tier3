# Sinfonia

Manages discovery of nearby cloudlets and deployment of backends for
edge-native applications.

Tier 1 is located in the cloud and it tracks availability of Tier 2 instances
at various cloudlets where backends can be deployed. Tier 3 is the client
application that mediates the discovery and deployment process for edge-native
applications.

This repository implements an example Tier3 client which can be used both as a
command-line application, and as a Python library.


## Installation

This should be installable with `pip install sinfonia-tier3`.


## Usage

The `sinfonia-tier3` application would normally be called by an edge-native
application to start an application specific backend on a nearby cloudlet.

The information normally provided by the app are the URL of a Tier1 instance
and the UUID identifying the needed backend. Finally the actual frontend
application and arguments that will be launched once the backend deployment has
started.

    $ sinfonia-tier3 <tier1-url> <uuid> <frontend-app> <args...>

An example application with UUID:00000000-0000-0000-0000-000000000000 (or the
convenient alias 'helloworld') starts an nginx server that will be accessible
with the hostname 'helloworld'.

    $ sinfonia-tier3 https://tier1.server.url/ helloworld /bin/sh
    sinfonia$ curl -v http://helloworld/
    ...
    sinfonia$ exit

When the frontend application exits, the network namespace and wireguard tunnel
are cleaned up. Any resources on the cloudlet are automatically released once
Tier2 notices the VPN tunnel has gone idle for some time


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


## Why does we need a sudo password when deploying

We need root access to create and configure a Wireguard tunnel endpoint that
connects the local application's network namespace/container to the deployed
backend. All of the code running as root is contained in
[src/sinfonia_tier3/root_helper.py](https://github.com/cmusatyalab/sinfonia-tier3/blob/main/src/sinfonia_tier3/root_helper.py)

Right now it runs the equivalent of,

```sh
ip link add wg-tunnel type wireguard
wg set wg-tunnel private-key <private-key> peer <public-key> endpoint ...
ip link set dev wg-tunnel netns <application network namespace>
```
