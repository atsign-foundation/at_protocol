# How atProtocol notifications work

## High level

```mermaid
flowchart LR
    subgraph bob
    BC("@bob atClient")
    BS("@bob atServer")
    end
    style alice fill:#def
    subgraph alice
    AC("@alice atClient")
    AS("@alice atServer")
    end
    BC -- "(1) monitor:" --> BS
    
    AC -- "(2) notify:" --> AS
    AS -- "(3) send to bob atServer" --> BS
    BS -- "(4) write to monitors" --> BC
```

## More detail

```mermaid
flowchart LR
    style AS fill:#def
    style alice fill:#def
    subgraph AS ["@alice atServer"]
        AS_NVH(notify verb handler)
        AS_DS(data store)
        AS_NS(notification subsystem)
    end
    subgraph BS ["@bob atServer"]
        BS_NVH(notify verb handler)
        BS_MVH(monitor verb handler)
        BS_DS(data store)
        BS_NS(notification subsystem)
    end
    BC -- "(1) monitor:" --> BS_MVH
    BS_MVH -- "(2) add this monitor" --> BS_NS
    subgraph alice
    AC("@alice atClient")
    end
    subgraph bob
    BC("@bob atClient")
    end
    
    AC -- "(3) notify:" --> AS_NVH
    AS_NVH -- "(4)" --> AS_NS
    AS_NS -- "(5)" --> AS_DS
    AS_NS -- "(6)" --> BS_NVH
    BS_NVH -- "(7)" --> BS_NS
    BS_NS -- "(8)" --> BS_DS
    BS_NS -- "(9) write to monitors" --> BC
```

## atClient to atServer 'PKAM' authentication

See [this diagram](./how-to-exchange-encrypted-data.md#sequence-diagram)

## atServer-to-atServer authentication

### 1) "from:@alice"

```mermaid
flowchart BT
    style alice fill:#def
    subgraph alice["alice atServer"]
        AS_OC(outbound connection)
        AS_DS(data store)
    end
    subgraph bob["bob atServer"]
        BS_ICH(inbound connection handler)
        BS_FVH(from handler)
    end
    AS_OC -- "(1) from @alice" --> BS_ICH
    BS_ICH -- "check cert" --> BS_ICH --> BS_FVH
    BS_FVH -- "(2) from response: proof" --> AS_OC
    AS_OC -- "(3) store proof" --> AS_DS
```

### 2) "pol" (proof of life)

```mermaid
flowchart LR
    subgraph bob
        BS_FVH(from handler)
        BS_PVH(pol handler)
    end
    style alice fill:#def
    subgraph alice
        AS_OC(outbound connection)
        AS_LVH(lookup handler)
        AS_DS(data store)
    end
    AS_OC -- "(4) pol" --> BS_PVH
    BS_PVH -- "(5) lookup challenge record" --> AS_LVH <--> AS_DS
    BS_PVH -- "(6) lookup signing public key" --> AS_LVH
    BS_PVH -- "(7) verify" --> BS_PVH
    BS_PVH -- "(8) connected prompt" --> AS_OC
```
