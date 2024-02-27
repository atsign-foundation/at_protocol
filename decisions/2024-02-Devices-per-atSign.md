# Devices per atSign

* **Status:** Draft
* **Last Updated:** 2024-02-23
* **Objective:** A standard supported maximum of devices per atSign to
engineer to.

## Context & Problem Statement

With each atSign it is possible to have N devices associated and connected at
any one time. With personal atSigns this is limited by the number of devices
a person may have. But in an Enterprise setting an atSign could have N devices.
With applications like SSH No Ports a company could have 10k devices all on
one atSign.

## Goals

Decide on a reasonable number of devices supported simulataneously on one
atSign and it associated atServer.

### Non-goals

We do not want to change the existing architecture and introduce complexity
to reduce the risk of an a single atSign's atServer being offline and
effecting huge numbers of devices in turn.

## Other considerations

Prevent a person using single atSign and connecting thousands of devices at
low cost and high risk and putting stress on the rest of the infrastructure.

* ### Option 1
  
  Keep existing atServer configuration see at what point things fail and
  decide on a % of that number of devices.

## Proposal Summary

Soft/advertised limit of 25 concurrent active devices per atSign

## Proposal in Detail

The existing limit of 200 TCP sessions and the existing limits of the docker
container holding the atServer provide good support for up to 50 devices, so
the suggested maximum should be 50% of that at 25 devices per atSign.
This provides ample devices for most if not all use cases and limits risk to
a maximum of 25 devices if an atServer fails whilst also protecting from
potential abuse of over subscribed atSigns.
