# Cellular telemetry through the QuecOpen API

The OpenWrt UI reads atomic JSON snapshots from `/tmp/air6-modem-status.json`.
`air6-modem-status`, supervised by procd, runs the read-only `air6-nw-api` helper
through a 20-second deadline every five seconds (configurable 2–60 seconds).
Only complete, successful registration snapshots replace the previous file.
RPC readers reject missing, malformed, future-dated or older-than-30-second data.
No status or cell RPC sends AT commands or runs a modem CLI. Explicit SMS,
debug-terminal and existing control actions keep their existing paths.

## Read APIs

```sh
ubus call luci.air6modem get_status
ubus call luci.air6modem get_cells
ubus call air6.cpe get_ca
ubus call air6.cpe get_band_lock
```

Existing authenticated rpcd ACLs apply; no public HTTP endpoint is added.
The snapshot contains IMSI, ICCID and IMEI, is mode 0600 and must not be uploaded
as public test evidence. No credentials, identity dumps or production keys are
needed in source control.

`get_cells` returns structured `cells`, `carriers`, `measurements`, `ca`, `endc`,
`api_errors`, `source`, `cache_age` and `stale` fields. Individual API failures
remain visible in `api_errors`; a failed section is empty/invalid rather than
reusing an earlier measurement. A failed whole snapshot becomes unavailable
after 30 seconds. The collector retries without a device reset or radio change.

## Fields and interpretation

- Cells: LTE/NR, serving or neighbour, PCI, ARFCN, cell ID, TAC, PLMN,
  RSRP/RSRQ/SINR/RSSI. NR SINR is dB; LTE SINR is converted from 0.1 dB.
  Sentinel identities and unavailable signal values are omitted/null.
- Carriers: LTE/NR PCC and SCC, band, PCI, ARFCN, downlink/uplink MHz,
  SCC activation and uplink configuration, MIMO layers, modulation indices,
  MCS and instantaneous API throughput in Kbytes/s. Bandwidth enum values are
  decoded using the SDK's separate LTE and NR tables.
- CA: configured and activated SCC counts, separately for LTE and NR.
  An LTE carrier plus an NR carrier alone does not establish intra-RAT CA.
- EN-DC: primary-cell availability, NR dual-connectivity restriction, and NSA
  registration. Availability and NSA registration do not establish that an NR
  secondary carrier is currently transmitting.
- Measurements: per-RAT PCC/SCC report indices for RSRP, RSRQ and SNR, RSSI dBm,
  rank indicator, path loss, best beam ID/RSRP and SSB measurements where reported.
  **3GPP report indices are displayed as indices, never labelled dBm or dB.**
- A carrier match supplies known serving-cell band/bandwidth. Neighbour
  band/bandwidth remain unknown when the API does not report them; overlapping
  n77/n78 ranges are not guessed from ARFCN.
- Temperature uses the maximum valid kernel `md*-thermal` reading, in Celsius,
  rather than an AT query. This differs from an AP/SoC maximum temperature.
- Selected band masks come from `ql_nw_get_band_mode(option=0)` and retain the
  existing word-order format used by the band-selection UI.

## Build and runtime requirements

Build `package/hcy/luci-app-air6-modem/compile` and
`package/hcy/air6-cpe-ui/compile`. The modem package has target architecture
and depends on `air6-modem-chain-only`, which supplies the existing proprietary
`libqlril` and `libql_uinf`. The helper also links OpenWrt's libubox/blobmsg JSON.
`air6-qlril-abi.h` contains the necessary ABI declarations, not vendor
implementation. These declarations were checked against the T830 SDK and
executed against the device's existing libraries; a different vendor ABI must
be verified before use. The existing compatibility libraries remain required.

The previous separate MIPC CA collector is retired; the UI now uses the same
snapshot for status, carriers and measurements. Explicit band-control writes
still use the existing serialized, read-back-verified transaction.

## Verification on 2026-11-11

- OpenWrt package compilation passed.
- Actual API calls returned registration, serving/neighbour cells, bands, CA,
  EN-DC, PCC measurements, identity and selected band masks.
- A complete API snapshot took approximately 50 ms on the test device.
- Thirty cached `get_cells` RPCs took 0.569 seconds including one SSH session;
  this is not a WAN throughput measurement or a per-call latency guarantee.
- Malformed/expired snapshots returned no old cells or carriers.
- Desktop/mobile browser rendering passed with no JavaScript errors and no
  automatically issued `run_at` RPCs when opening the cellular page.
- Original files were backed up and restored byte for byte in a separate tree.

The network observed during these checks had one NR PCC; multi-carrier CA,
active NSA dual connectivity and China Mobile n41 were **not** verified.
This UI change does not add RF support or prove a P54 modem migration works.

## Supplied diagnostic material

The cellular-data-path note correctly identified the native RIL path and was
used as reference material. ModemMETA and ELT Lite archives contain Windows
installers; they are diagnostic tools and are not installed on the router.
The supplied UE NR capability text is a decoded capability example, useful for
CA analysis, rather than an OpenWrt runtime API implementation or proof of
currently active carriers.

The read-only smoke-test script is in the companion [OpenWrt repository](https://github.com/hchyhchyxh/openwrt-air6/blob/main/scripts/test-cellular-telemetry.py).
