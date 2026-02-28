# C/C++ to Rust Migration: Market Size Assessment

## Executive Summary

The C/C++ to Rust modernization opportunity is potentially 5-10x larger than
COBOL modernization, but it is earlier-stage and less defined as a market
category. No major analyst firm has sized it separately -- it is embedded
within the broader $15-51B application modernization market.

| Metric | COBOL | C/C++ |
|--------|-------|-------|
| Estimated active codebase | 800B-1.5T lines | Tens to hundreds of billions |
| Modernization market size | $1.7-3.12B (2024) | No separate estimate (est. $5-15B addressable) |
| Developer population | ~500K-800K (declining) | 16.3M (growing 73% since 2022) |
| Government pressure | Moderate (aging workforce) | High (White House, CISA, NSA, DoD directives) |
| Migration driver | Talent extinction | Security/safety mandates |
| Tooling maturity | Multiple commercial vendors | Early stage (c2rust + research tools) |

---

## 1. Scale of C/C++ Code

**Known data points:**

- Microsoft alone: ~1 billion lines of C/C++
- Linux kernel: ~40 million lines (predominantly C), growing ~400K lines every 2 months
- Windows: ~50 million lines (estimated, predominantly C/C++)
- Android (AOSP): 92-250+ million lines depending on scope

**Total estimate**: Tens to hundreds of billions of lines globally when
aggregating operating systems, embedded firmware, financial systems, telecom,
automotive ECUs, aerospace, games, and enterprise applications. There is no
authoritative global census.

---

## 2. Developer Population

Source: SlashData Global Developer Population Trends 2025

- C/C++ developers: **16.3 million** (2025), up from 9.4M in 2022 (73% growth)
- Global developers total: 47.2 million
- C/C++ share: ~34% of all developers
- TIOBE Index (Feb 2025): C++ at #2 (11.37%), C at #4 (9.84%)

**Trend**: Growing, not shrinking. Embedded software developer population
more than doubled since 2022, driven by connected devices, automotive, and
custom hardware.

This is the key difference from COBOL: the C/C++ developer base is massive
and expanding, so migration is driven by security, not talent scarcity.

---

## 3. Critical Infrastructure Penetration

| Sector | C/C++ Penetration | Notes |
|--------|-------------------|-------|
| Embedded systems | >95% | C: 60-70%, C++: 20-25% |
| Operating systems | ~100% of kernels | Linux, Windows, macOS, Android HAL |
| Financial trading | Dominant for HFT | Latency-critical, less migration pressure |
| Automotive ECUs | Standard (MISRA) | ISO 26262 compliance required |
| Aerospace/avionics | Dominant | DO-178C certification |
| Telecom/networking | Core stacks | Growing 5G security concerns |
| Medical devices | Dominant | IEC 62304, FDA cybersecurity focus |

---

## 4. Cost of Memory Safety Bugs

- Microsoft: ~70% of CVEs each year are memory safety issues (consistent over decade+)
- Google/Chromium: ~70% of serious security bugs are memory safety issues
- Global cybercrime damages: estimated >$9.5T in 2025
- NIST (2002): Software bugs cost U.S. economy $59.5B annually (all bugs, not just memory)

**Derived estimate**: If 70% of vulnerabilities are memory-safety related, the
annual cost of memory safety vulnerabilities (exploitation + patching +
incident response + breach costs) is likely tens to hundreds of billions of
dollars globally. No single authoritative figure exists.

---

## 5. Rust Adoption

| Metric | Value | Source |
|--------|-------|--------|
| Rust developers | 2.27M (used in 12 months); 709K primary | JetBrains 2024 |
| Stack Overflow "most admired" | #1 for 9 consecutive years (2016-2024) | SO Survey |
| GitHub YoY growth | 40% | Octoverse 2023 |
| Commercial usage growth | 68.75% increase (2021-2024) | JetBrains |
| Enterprise production use | 45% of enterprises run Rust in non-trivial workloads | 2025 surveys |
| Safety-critical qualification | Ferrocene: ISO 26262 ASIL-D, IEC 61508 SIL-4 | Ferrous Systems |

---

## 6. Migration Market Landscape

### Broader Market Context

| Market | Size (2024) | Projected | CAGR |
|--------|-------------|-----------|------|
| Application Modernization Services | $19.82B | $39.62B (2029) | 14.6% |
| Legacy Software Modernization | $15.14B (2025) | $27.3B (2029) | 15.9% |
| Mainframe Modernization (COBOL/PL/I) | -- | $13.34B (2030) | -- |
| COBOL Modernization (specific) | $1.7-3.12B | $5.3-8.59B (2033) | ~14% |
| C/C++ Migration (estimated) | Not tracked | Est. $5-15B addressable | Unknown |

### VC-Funded Companies

| Company | Total Funding | Focus |
|---------|--------------|-------|
| Code Metal | ~$161.5M ($36.5M Series A + $125M Series B) | AI-powered code translation (C/C++/COBOL to Rust) |
| Immunant | ~$10M (DARPA contracts) | c2rust transpiler + consulting |

### Government Funding

| Program | Amount | Focus |
|---------|--------|-------|
| DARPA TRACTOR | $14M | Automated C-to-Rust via LLMs + formal methods |
| DARPA CFAR/RADSS | ~$10M (shared) | c2rust development |

### Big Tech Internal Investment

| Company | Status | Scale |
|---------|--------|-------|
| Microsoft | Goal: eliminate all C/C++ by 2030 | 188K+ lines rewritten; 1B total target |
| Google | Rust default for new Android system code | Memory vulns below 20% |
| Meta | Mononoke (source control) + messaging rewrite | Production since 2016 |
| AWS | Firecracker, S3, EC2, CloudFront components | Multiple core services |

### Consulting Firms

| Firm | Location | Specialty |
|------|----------|-----------|
| Ferrous Systems | Berlin | Rust consulting, embedded, Ferrocene compiler |
| corrode | Dusseldorf | Rust migration guides, training, consulting |
| Immunant | USA | c2rust, safe Rust interfaces |
| Tweede Golf | Netherlands | Rust engineering, embedded, sudo-rs |
| Ardan Labs | USA | Rust training (corporate, premium) |
| Evrone | Global | Full Rust development, migration |

---

## 7. Open-Source Tooling Maturity

### Production-Ready

| Tool | Maturity | Limitation |
|------|----------|------------|
| c2rust (Immunant) | v0.21 (Oct 2025) | Output is unsafe, non-idiomatic Rust |

### Research / Academic (Not Production-Ready)

| Tool | Description | Status |
|------|-------------|--------|
| C2SaferRust | Reduces unsafe in c2rust output by up to 38% | Paper (Jan 2025) |
| SACTOR | LLM + static analysis for idiomatic Rust | Paper (2025) |
| Rustine | 100% compilation success, full automation | Paper (2025) |
| RustMap | Project-scale C-to-Rust via program analysis + LLM | Paper (2025) |
| SmartC2Rust | Iterative LLM-driven translation | Paper (2025) |
| LAC2R | Monte Carlo Tree Search + LLM | Paper (2025) |
| FORCES | Incremental C/C++ to Rust for robotics | ICRA 2025 |

**Key gap**: No tool currently produces idiomatic, safe Rust from C at
production scale without significant human intervention. c2rust compiles and
runs but output is wrapped in unsafe blocks. This is the gap that DARPA
TRACTOR and Code Metal are both targeting.

---

## 8. Enterprise Adoption

| Organization | What | Impact |
|-------------|------|--------|
| Microsoft | Windows kernel (36K lines), DirectWrite (152K lines) | Research target: 1 engineer, 1 month, 1M lines |
| Google Android | System services, kernel modules | Memory vulns 76% -> below 20%; 4x lower rollback |
| Meta | Mononoke source control, messaging server | 2-4 orders of magnitude perf improvement |
| AWS | Firecracker (Lambda), S3, EC2, CloudFront | Core infrastructure in production |
| Epic Games | Unreal audio pipeline | 92% crash reduction, 15% perf gain |
| Cloudflare | Infire LLM inference engine | 7% faster than vLLM |
| Linux kernel | ASIX PHY driver, ashmem allocator | Deployed on millions of devices |
| Ubuntu | sudo-rs default in 25.10 | Replaces C sudo on all Ubuntu installs |

---

## 9. Key Assessment

### Why This Opportunity Is Larger Than COBOL

1. **Code volume**: Tens-to-hundreds of billions of lines vs 800B-1.5T for COBOL
2. **Government mandates**: White House, NSA, CISA, DoD all explicitly calling
   for migration -- stronger than anything COBOL modernization has received
3. **Security economics**: 70% of CVEs are memory safety, cybercrime >$9.5T/yr
4. **Sector breadth**: Automotive, aerospace, medical, telecom, OS, cloud --
   not just financial mainframes
5. **Active VC interest**: Code Metal at $161.5M+ vs fragmented COBOL market
6. **DARPA funding**: Direct government R&D investment ($14M+ TRACTOR)

### Why It Is Harder to Define

1. **No talent crisis**: 16.3M C/C++ developers and growing -- no urgency
   from workforce scarcity
2. **Performance requirements**: Some sectors (HFT, gaming) have no incentive
   to move away from C++
3. **Tooling immaturity**: No production-grade automated safe translation exists
4. **Certification barriers**: Automotive, aerospace, medical all require
   re-certification after language change
5. **Incremental nature**: Migration happens module-by-module, not system-by-system
6. **curl/hyper lesson**: Even well-funded incremental adoption in mature C
   projects can fail (curl dropped Rust backend Dec 2024)

### Where the Money Will Flow

1. **AI-assisted translation tools** (Code Metal, DARPA TRACTOR)
2. **Safety-critical Rust toolchains** (Ferrous Systems / Ferrocene)
3. **Consulting/migration services** (growing as enterprises start migrating)
4. **Training** (16.3M C/C++ devs need Rust skills)
5. **Interop tooling** (C/Rust FFI, bindgen, cxx -- bridging during migration)

---

## Confidence Levels

| Claim | Confidence |
|-------|-----------|
| 16.3M C/C++ developers globally | HIGH (SlashData primary survey) |
| 70% of CVEs are memory safety | HIGH (Microsoft + Google independently) |
| C/C++ >95% of embedded systems | MEDIUM-HIGH (industry surveys) |
| Total C/C++ code volume | MEDIUM (extrapolated, no census) |
| C/C++ migration market $5-15B | LOW (my derivation, no analyst report) |
| Annual cost of memory safety bugs | LOW-MEDIUM (derived from 70% x cybercrime) |
| COBOL modernization $1.7-3.12B | HIGH (analyst reports) |
| Rust developer count 2.27M | HIGH (JetBrains primary survey) |
| Code Metal $161.5M funding | HIGH (CNBC, TechBuzz reporting) |
