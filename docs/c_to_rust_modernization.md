# C/C++ to Rust Modernization: Reference Document

The most significant language modernization effort in computing today is the
push to replace C/C++ with Rust for memory safety. Unlike COBOL modernization
(driven by talent extinction), C modernization is driven by a structural class
of vulnerabilities -- buffer overflows, use-after-free, null pointer
dereferences -- that memory-safe languages eliminate by design.

---

## 1. US Government Directives

### 1.1 White House ONCD Report (February 2024)

"Back to the Building Blocks: A Path Toward Secure and Measurable Software"

The White House Office of the National Cyber Director called on the technology
community to adopt memory-safe programming languages (Rust, Go, Java, C#,
Python, Swift). The report argues that memory safety vulnerabilities have
plagued the digital ecosystem for 35 years and are the root cause behind many
critical cyber incidents.

- Full Report (PDF): https://bidenwhitehouse.archives.gov/wp-content/uploads/2024/02/Final-ONCD-Technical-Report.pdf
- Press Release: https://bidenwhitehouse.archives.gov/oncd/briefing-room/2024/02/26/press-release-technical-report/
- Fact Sheet: https://bidenwhitehouse.archives.gov/oncd/briefing-room/2024/02/26/memory-safety-fact-sheet/

### 1.2 NSA Guidance

"Software Memory Safety" -- Cybersecurity Information Sheet (November 2022).
Recommends organizations shift from C/C++ to memory-safe languages. States
that poor memory management causes over 70% of exploitable vulnerabilities.

- NSA CSI (PDF): https://media.defense.gov/2022/Nov/10/2003112742/-1/-1/0/CSI_SOFTWARE_MEMORY_SAFETY.PDF

"Memory Safe Languages: Reducing Vulnerabilities" (June 2025). Joint NSA/CISA
publication on obstacles and solutions for adopting memory-safe languages.

- Joint CSI (PDF): https://media.defense.gov/2025/Jun/23/2003742198/-1/-1/0/CSI_MEMORY_SAFE_LANGUAGES_REDUCING_VULNERABILITIES_IN_MODERN_SOFTWARE_DEVELOPMENT.PDF
- NSA Press Release: https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/Article/4223298/nsa-and-cisa-release-csi-highlighting-importance-of-memory-safe-languages-in-so/

### 1.3 CISA Guidance

"The Case for Memory Safe Roadmaps" (December 2023). Joint guide from CISA,
NSA, FBI, and international partners.

- Landing Page: https://www.cisa.gov/case-memory-safe-roadmaps
- Full Document (PDF): https://www.cisa.gov/sites/default/files/2023-12/The-Case-for-Memory-Safe-Roadmaps-508c.pdf
- Alert: https://www.cisa.gov/news-events/alerts/2023/12/06/cisa-releases-joint-guide-software-manufacturers-case-memory-safe-roadmaps

"Exploring Memory Safety in Critical Open Source Projects" (June 2024):

- Alert: https://www.cisa.gov/news-events/alerts/2024/06/26/cisa-and-partners-release-guidance-exploring-memory-safety-critical-open-source-projects

CSAC Advisory Committee Recommendations (December 2023):

- Report (PDF): https://www.cisa.gov/sites/default/files/2023-12/CSAC_TAC_Recommendations-Memory-Safety_Final_20231205_508.pdf

---

## 2. DARPA TRACTOR Program

TRACTOR: TRanslating All C TO Rust. Announced mid-2024. Aims to automate
translation of legacy C code to idiomatic, safe Rust using LLMs combined with
static and dynamic analysis. Goal: produce Rust code of the same quality a
skilled human developer would write, eliminating the entire class of memory
safety vulnerabilities. Solicitation DARPA-PS-24-20 issued September 8, 2024.

- Program Page: https://www.darpa.mil/research/programs/translating-all-c-to-rust
- News: https://www.darpa.mil/news/2024/memory-safety-vulnerabilities
- Proposers Day: https://www.darpa.mil/news-events/tractor-proposers-day
- UIUC Partnership: https://csl.illinois.edu/news-and-media/translating-legacy-code-for-a-safer-future-darpa-backs-effort-to-convert-c-to-rust

---

## 3. Google

### 3.1 Android Rust Adoption

Results after shifting new Android development to memory-safe languages:

- Memory safety vulnerabilities: 76% of all Android vulns (2019) -> 24% (2024) -> below 20% (2025)
- Absolute count: 223 memory safety bugs (2019) -> fewer than 50 (2024)
- 1,000x reduction in memory safety vulnerability density (Rust vs C/C++)
- Rust code: 20% fewer revisions, 25% less code review time, 4x lower rollback rate vs C++

Key blog posts:

- "Eliminating Memory Safety Vulnerabilities at the Source" (Sep 2024): https://security.googleblog.com/2024/09/eliminating-memory-safety-vulnerabilities-Android.html
- "Rust in Android: move fast and fix things" (Nov 2025): https://security.googleblog.com/2025/11/rust-in-android-move-fast-fix-things.html
- "Memory Safe Languages in Android 13" (Dec 2022): https://security.googleblog.com/2022/12/memory-safe-languages-in-android-13.html
- "Secure by Design: Google's Perspective" (Mar 2024): https://security.googleblog.com/2024/03/secure-by-design-googles-perspective-on.html
- "Safer with Google: Advancing Memory Safety" (Oct 2024): https://security.googleblog.com/2024/10/safer-with-google-advancing-memory.html

### 3.2 Chromium / Chrome

Chromium independently reported ~70% of serious security bugs are memory
safety problems. Rust support announced January 2023, production-ready by
Chrome 119 (late 2023). Over 1,000 Google developers have committed Rust code.

- "Supporting the Use of Rust in Chromium" (Jan 2023): https://security.googleblog.com/2023/01/supporting-use-of-rust-in-chromium.html
- Memory Safety Overview: https://www.chromium.org/Home/chromium-security/memory-safety/
- "Improving Interoperability Between Rust and C++" (Feb 2024): https://security.googleblog.com/2024/02/improving-interoperability-between-rust-and-c.html

---

## 4. Microsoft

### 4.1 Memory Safety CVE Statistics

Approximately 70% of CVEs Microsoft assigns each year are caused by memory
safety issues in C/C++ code.

- "A proactive approach to more secure code" (Jul 2019): https://msrc.microsoft.com/blog/2019/07/a-proactive-approach-to-more-secure-code/
- "We need a safer systems programming language" (Jul 2019): https://www.microsoft.com/en-us/msrc/blog/2019/07/we-need-a-safer-systems-programming-language
- "Why Rust for safe systems programming" (Jul 2019): https://msrc.microsoft.com/blog/2019/07/why-rust-for-safe-systems-programming/

### 4.2 Rust in Windows (Secure Future Initiative)

Under the SFI (announced November 2023):

- 36,000 lines of Rust in the Windows kernel (win32kbase_rs.sys in System32)
- 152,000 lines of Rust in DirectWriteCore (font parsing), ported from C++ in 6 months
- Surface devices use Rust-based UEFI firmware and Secure Embedded Controller
- Surface pioneering Windows drivers written in Rust
- October 2025: open-sourced "Patina", a UEFI boot firmware written from scratch in Rust

References:

- SFI Report Nov 2025: https://blogs.windows.com/windowsexperience/2025/11/10/advancing-security-with-windows-and-surface-microsoft-sfi-report-nov-2025/
- SFI Progress Report: https://www.microsoft.com/en-us/trust-center/security/secure-future-initiative/sfi-progress-report-november-2025
- Secure by Design (Apr 2025): https://www.microsoft.com/en-us/security/blog/2025/04/17/microsofts-secure-by-design-journey-one-year-of-success/

---

## 5. Linux Kernel

### 5.1 Initial Acceptance (Linux 6.1, December 2022)

Linus Torvalds confirmed Rust for Linux 6.1. Initial 12,500-line Rust
infrastructure merged October 2022.

- Phoronix: https://www.phoronix.com/news/Rust-Is-Merged-Linux-6.1
- Wikipedia: https://en.wikipedia.org/wiki/Rust_for_Linux

### 5.2 First Rust Driver (Linux 6.8, Early 2024)

ASIX PHY network driver -- rewrite of existing ax88796b C driver. First
user-visible Rust code in the kernel.

- Phoronix: https://www.phoronix.com/news/Linux-6.8-Rust-PHY-Driver
- Rust for Linux: https://rust-for-linux.com/asix-phy-driver

### 5.3 Rust No Longer Experimental (Linux 7.0, 2025)

Rust officially concluded as experimental -- now a first-class language
alongside C.

- Phoronix: https://www.phoronix.com/news/Linux-7.0-Rust

---

## 6. Major Open-Source Projects

### 6.1 sudo-rs (Rust Rewrite of sudo/su)

Funded by ISRG Prossimo project (Dec 2022). Developed by Tweede Golf and
Ferrous Systems. Stable release August 2023. One-third of historical sudo
security bugs were memory management issues. Will become default sudo in
Ubuntu 25.10 (2025).

- Prossimo Initiative: https://www.memorysafety.org/initiative/sudo-su/
- Stable Release Blog: https://www.memorysafety.org/blog/sudo-first-stable-release/
- GitHub: https://github.com/trifectatechfoundation/sudo-rs
- Ubuntu Default: https://www.memorysafety.org/blog/sudo-rs-headed-to-ubuntu/

### 6.2 curl -- Hyper (Rust HTTP Backend)

ISRG funded Daniel Stenberg to integrate Hyper (Rust HTTP library) as
optional curl backend (2020). However, in December 2024 Stenberg announced
hyper support would be dropped from curl 8.12.0 due to insufficient adoption.
This is a significant data point about incremental Rust adoption challenges in
mature C codebases.

- "dropping hyper" (Dec 2024): https://daniel.haxx.se/blog/2024/12/21/dropping-hyper/
- "rust in curl with hyper" (Oct 2020): https://daniel.haxx.se/blog/2020/10/09/rust-in-curl-with-hyper/
- Prossimo Initiative: https://www.memorysafety.org/initiative/curl/

### 6.3 Prossimo / ISRG -- Memory Safety Infrastructure

Prossimo (by ISRG, the Let's Encrypt organization) drives memory-safe
rewrites of critical internet infrastructure:

- **Rustls** -- Memory-safe TLS library, now faster than most TLS implementations
- **ntpd-rs** -- Memory-safe NTP, deployed in Let's Encrypt production (2024)
- **Hickory DNS** -- Memory-safe recursive DNS resolver, targeting production mid-2026
- **rav1d** -- Memory-safe AV1 decoder

References:

- Home: https://www.memorysafety.org/
- Blog: https://www.memorysafety.org/blog/
- Rustls: https://www.memorysafety.org/initiative/rustls/
- ntpd-rs Deployment: https://www.memorysafety.org/blog/ntpd-rs-deployment/
- AWS $1M Commitment: https://www.memorysafety.org/blog/aws-funding/

---

## 7. Industry Consortiums and Foundations

### 7.1 Safety-Critical Rust Consortium (June 2024)

Announced by Rust Foundation with AdaCore, Arm, Ferrous Systems, HighTec,
Lynx Software, OxidOS, Veecle, Woven by Toyota, and others. Supports Rust
in safety-critical software (aerospace, automotive, finance, defense).

- Announcement: https://rustfoundation.org/media/announcing-the-safety-critical-rust-consortium/
- GitHub: https://github.com/rustfoundation/safety-critical-rust-consortium
- Ferrous Systems Blog: https://ferrous-systems.com/blog/new-safety-critical-rust-consortium/

### 7.2 OpenSSF Alpha-Omega -- Rust Foundation Security

$460K grant to Rust Foundation (2022) for Security Initiative. Additional
$216K (2024) for Trusted Publishing on crates.io.

- Alpha-Omega 2024: https://openssf.org/blog/2023/11/15/alpha-omega-to-continue-support-of-rust-foundation-security-initiative-in-2024/
- Progress Update: https://rustfoundation.org/media/strengthening-rust-security-with-alpha-omega-a-progress-update/

### 7.3 Rust Foundation

Members include Google, Microsoft, AWS, Huawei, Meta, and others.

- 2025 Year in Review: https://rustfoundation.org/2025/
- Unsafe Rust in the Wild Report: https://rustfoundation.org/media/unsafe-rust-in-the-wild-notes-on-the-current-state-of-unsafe-rust/

---

## 8. Academic Research -- C-to-Rust Translation

### 8.1 Foundational

"Aliasing Limits on Translating C to Safe Rust" -- Emre et al., OOPSLA 2023.
Only 12-21% of C pointers can be translated to safe Rust references due to
borrow checker aliasing constraints.

- ACM: https://dl.acm.org/doi/abs/10.1145/3586046
- PDF: https://www.cs.usfca.edu/~memre/oopsla23-aliasing-limits.pdf

"Ownership Guided C to Rust Translation" -- Springer.

- Springer: https://link.springer.com/chapter/10.1007/978-3-031-37709-9_22
- PDF: https://oro.open.ac.uk/89190/8/89190VOR.pdf

### 8.2 LLM-Based Approaches (2024-2025)

"Type-migrating C-to-Rust Translation Using a Large Language Model" --
Empirical Software Engineering, October 2024.

- Springer: https://link.springer.com/article/10.1007/s10664-024-10573-2

"SACTOR: LLM-Driven Correct and Idiomatic C to Rust" -- Two-step
methodology augmenting LLMs with static-analysis hints.

- arXiv: https://arxiv.org/pdf/2503.12511

"C2SaferRust: Transforming C Projects into Safer Rust" (January 2025).
Reduces raw pointer declarations by up to 38%, unsafe code by up to 28%.

- arXiv: https://www.arxiv.org/pdf/2501.14257

"Translating Large-Scale C Repositories to Idiomatic Rust" (Rustine).
100% compilation success and functional equivalence through full automation.

- arXiv: https://arxiv.org/pdf/2511.20617

"RustMap: Project-Scale C-to-Rust Migration via Program Analysis and LLM".

- Springer: https://link.springer.com/chapter/10.1007/978-3-032-00828-2_16

### 8.3 Benchmarks

"CRUST-Bench: Comprehensive Benchmark for C-to-safe-Rust Transpilation" --
UT Austin. Fully automated safe transpilation remains an open challenge.

- PDF: https://www.cs.utexas.edu/~isil/crust-bench.pdf

"Translating C To Rust: Lessons from a User Study" -- NDSS 2025. Tools like
c2rust produce compiling Rust but code remains largely unsafe.

- NDSS PDF: https://www.ndss-symposium.org/wp-content/uploads/2025-1407-paper.pdf

### 8.4 Tools

**C2Rust (Immunant/Galois)** -- Most widely referenced C-to-Rust transpiler.
Translates C99 code to (unsafe) Rust.

- GitHub: https://github.com/immunant/c2rust
- Demo: https://c2rust.com/

---

## Summary Timeline

| Date | Event |
|------|-------|
| Jul 2019 | Microsoft MSRC: 70% of CVEs are memory safety issues |
| Nov 2022 | NSA publishes "Software Memory Safety" CSI |
| Dec 2022 | Rust infrastructure merged into Linux 6.1 |
| Jan 2023 | Google announces Rust support in Chromium |
| Aug 2023 | sudo-rs first stable release |
| Dec 2023 | CISA publishes "The Case for Memory Safe Roadmaps" |
| Feb 2024 | White House ONCD publishes memory-safe languages report |
| Early 2024 | First Rust driver (ASIX PHY) merged into Linux 6.8 |
| Jun 2024 | Safety-Critical Rust Consortium announced |
| Sep 2024 | Google: 68% drop in Android memory safety bugs |
| Sep 2024 | DARPA TRACTOR solicitation issued |
| Dec 2024 | curl drops hyper (Rust HTTP backend) |
| Nov 2025 | Microsoft SFI: Rust in Windows kernel, DirectWrite, Surface |
| Nov 2025 | Google: Android memory safety bugs below 20% |
| 2025 | Linux 7.0 concludes Rust experiment -- first-class language |
| 2025 | sudo-rs becomes default sudo in Ubuntu 25.10 |

---

## Relevance to Corpus Builder

The C-to-Rust modernization push is directly relevant:

1. **Parallel problem**: Just as COBOL modernization needs representative
   enterprise COBOL code, C-to-Rust translation tools need representative
   C codebases for training and validation.

2. **DARPA TRACTOR**: DARPA is explicitly funding automated C-to-Rust
   translation -- a direct analog to COBOL-to-modern-language translation.

3. **Corpus availability**: Unlike COBOL, massive C codebases ARE publicly
   available (Linux kernel, curl, OpenSSL, FFmpeg, etc.), making a C corpus
   far more tractable to build.

4. **Research demand**: The volume of 2024-2025 papers on LLM-based C-to-Rust
   translation shows active demand for training/evaluation datasets.

5. **curl/hyper failure**: The December 2024 curl/hyper discontinuation
   demonstrates that even well-funded incremental Rust adoption in mature C
   projects faces real practical barriers -- validating the need for better
   automated translation tools.
