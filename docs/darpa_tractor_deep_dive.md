# DARPA TRACTOR Deep Dive

TRACTOR: TRanslating All C TO Rust. DARPA's flagship program to automate
migration of legacy C code to safe, idiomatic Rust.

---

## Program Overview

- **Program Manager**: Dr. Dan S. Wallach (Rice University professor, DARPA I2O since June 2023)
- **Office**: Information Innovation Office (I2O)
- **Announced**: July 31, 2024
- **Solicitation**: DARPA-PS-24-20 (September 8, 2024)
- **Expected end**: Late 2027 (based on Aarno Labs contract: June 2025 - December 2027)
- **Budget**: Not fully disclosed; estimated ~$14M across ~7 teams
- **T&E**: MIT Lincoln Laboratory (independent evaluation)

---

## Technical Areas

**TA1 -- C to Rust Translation Research**: Core applied research. Automated
translation of legacy C to safe, idiomatic Rust using combinations of static
analysis, dynamic analysis, and LLMs. Target: "same quality and style that a
skilled Rust developer would employ."

**TA2 -- Theoretical Translation Research**: Formal-methods-oriented.
Multi-threaded C programs with POSIX threads, machine-specific memory
semantics. Translating these to Rust's structured concurrency model.
"Defining equivalence in this context is a significant research challenge."

---

## Known Performers

### ForCLift Consortium -- $5M

"Formally-Verified Compositional Lifting of C to Rust"

- **Lead**: Somesh Jha, University of Wisconsin-Madison
- **Co-PIs**: Sanjit Seshia (UC Berkeley), Alvin Cheung (UC Berkeley),
  Elizabeth Polgreen (Edinburgh), Varun Chandrasekaran (UIUC), Tej Chajed (UW-Madison)
- **Approach**: Verified Lifting -- combining formal methods, program analysis,
  and LLMs. Recognizes idioms (arrays, pointer arithmetic), converts unsafe
  constructs to safe ones (C arrays -> Vec, pointer arithmetic -> slices),
  uses formal verification to confirm translations preserve semantics.
- Source: https://csl.illinois.edu/news-and-media/translating-legacy-code-for-a-safer-future-darpa-backs-effort-to-convert-c-to-rust

### Aarno Labs -- Tenjin Project (undisclosed amount)

- **PI**: Dr. Benjamin Karel (Aarno Labs)
- **Collaborators**: Michael Carbin (MIT CSAIL), Martin Rinard (MIT CSAIL)
- **Duration**: June 2025 - December 2027
- **Approach**: Deterministic translation framework using multi-stage pipeline:
  - Static analysis via CodeHawk abstract interpretation engine
  - Dynamic analysis via DIODE input synthesis system
  - Staged translation: type signatures first, then function bodies
  - Semantic modeling of ownership, lifetimes, and aliasing
  - Accepts human or LLM guidance but focuses on deterministic, verifiable output
- **Deliverable**: Open-source tools for public and private sector
- Source: https://www.aarno-labs.com/project/tenjin/

### Other Performers

Additional teams are believed to exist but have not publicly announced.
Notable absentees from public announcements (despite deep C-to-Rust
expertise): Immunant (c2rust creators), Galois, Trail of Bits, GrammaTech.

---

## Evaluation Benchmarks (MIT Lincoln Lab)

Benchmarks released on 6-month cadence with increasing complexity:

- **Battery 01 -- Basic C Features**: Constrained C subset, well-defined pointer
  lifetimes, pass-by-reference, error handling, global/static structures
- **Milestone 0 -- Perlin Noise Library**: Numerical computation, array manipulation
- **Milestone 1 -- SPHINCS Crypto Library**: Bit manipulation, security-critical
  correctness, strict performance requirements

Round 1 Evaluation Report completed. Test corpus on GitHub.
Contact: tractor@ll.mit.edu
MIT Lincoln Lab: https://www.ll.mit.edu/tractor

---

## Definition of Success

TRACTOR defines success beyond mere compilation:

- **Safe**: No unsafe blocks (or minimal, well-justified)
- **Idiomatic**: Proper Vec, Option/Result, iterators, pattern matching, lifetimes
- **Readable**: "Not enough to yield Rust code that is safe but unreadable"
- **Functionally equivalent**: Preserves original semantics
- **Performance-preserving**: No degradation

c2rust is the explicit anti-pattern -- compiles and runs but saturated with
unsafe blocks and "has exactly the semantics of C pointers."

Target: 99% automation for 100x cost reduction vs manual rewriting.

---

## Program Lineage

CFAR (Cyber Fault-tolerant Attack Recovery)
  -> RADSS (Robust Assured Diversity, ~$10M, Galois + Trail of Bits + Immunant + UC Irvine)
    -> c2rust (developed by Immunant under DARPA funding)
      -> TRACTOR (building on c2rust baseline to achieve idiomatic safe Rust)

Related Wallach-managed programs:
- V-SPELLS: Incremental replacement of legacy components with verified code
- SafeDocs: Verified parsers for electronic data formats
- SIEVE: Zero-knowledge proofs for capability verification
- E-BOSS: Enhanced SBOMs for software sustainment

---

## Open Challenges (Acknowledged by DARPA)

1. **LLM hallucination**: "LLMs can hallucinate incorrect answers" -- Wallach
2. **Pointer semantics gap**: C pointer arithmetic has no safe Rust equivalent
3. **Limited Rust training data**: Less LLM training data for Rust than C
4. **Concurrency translation**: POSIX threads -> Rust structured concurrency
   requires novel formal methods
5. **Readability vs correctness tradeoff**: Working code != maintainable code
6. **Scale**: Manual rewriting "can take years and cost billions of dollars"
7. **High-risk bet**: DARPA acknowledges 85-90% of projects fail full objectives

---

## Community Criticism

**Rust community (users.rust-lang.org)**:
- "Using an extremely complicated, stochastic black box to translate
  mission-critical code is a terrible idea"
- "Fixing C programs to be idiomatic Rust isn't a local transformation"
- Concern about what "idiomatic Rust" means when original C was never
  designed with ownership model in mind

**Hacker News**:
- Testing c2rust on buggy JPEG decoder produced identical segfaults in C
  and translated unsafe Rust -- syntactic translation preserves bugs
- Alternative approaches cited: Fil-C (memory-safe C runtime checking),
  SaferCPlusPlus/scpptool (restricted safe C++ subset)

**The Register**: "A DARPA-hard problem" with "daunting edge cases"

**Honest assessment**: The program seems clear-eyed about difficulty. The
six-month benchmark cadence with increasing complexity suggests incremental,
evidence-based approach. Even partial success (handling 80-90% of patterns
with human intervention for edge cases) would be valuable.

---

## Key URLs

Program:
- DARPA page: https://www.darpa.mil/research/programs/translating-all-c-to-rust
- DARPA news: https://www.darpa.mil/news/2024/memory-safety-vulnerabilities
- Wallach bio: https://www.darpa.mil/about/people/dan-wallach
- MIT Lincoln Lab T&E: https://www.ll.mit.edu/tractor

Solicitations:
- SAM.gov (SN-24-89): https://sam.gov/opp/1e45d648886b4e9ca91890285af77eb7/view
- SAM.gov (PS-24-20): https://sam.gov/opp/dca883c8df494524a24250892e6b5e1d/view

Performers:
- ForCLift (UIUC): https://csl.illinois.edu/news-and-media/translating-legacy-code-for-a-safer-future-darpa-backs-effort-to-convert-c-to-rust
- Aarno Labs Tenjin: https://www.aarno-labs.com/project/tenjin/
- Aarno Labs announcement: https://www.aarno-labs.com/blog/post/news-aarno-labs-awarded-darpa-grant-to-develop-tools-for-translating-c-to-safe-rust/

Predecessors:
- c2rust: https://github.com/immunant/c2rust
- Galois RADSS: https://www.galois.com/project/radss
- V-SPELLS: https://www.darpa.mil/research/programs/verified-security-and-performance-enhancement-of-large-legacy-software

Community discussion:
- Rust forum (2024): https://users.rust-lang.org/t/darpa-translating-all-c-to-rust-tractor/115242
- Rust forum (2025): https://users.rust-lang.org/t/darpa-tractor-program-c-to-rust-conversion/133653
- Hacker News: https://news.ycombinator.com/item?id=45443368
- The Register: https://www.theregister.com/2024/08/03/darpa_c_to_rust/
- Dark Reading: https://www.darkreading.com/application-security/darpa-aims-to-ditch-c-code-move-to-rust

Policy context:
- White House ONCD report: https://bidenwhitehouse.archives.gov/wp-content/uploads/2024/02/Final-ONCD-Technical-Report.pdf
- NSA/CISA 2025 guidance: https://media.defense.gov/2025/Jun/23/2003742198/-1/-1/1/CSI_MEMORY_SAFE_LANGUAGES_REDUCING_VULNERABILITIES_IN_MODERN_SOFTWARE_DEVELOPMENT.PDF
