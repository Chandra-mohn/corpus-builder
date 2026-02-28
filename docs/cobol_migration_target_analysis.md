# COBOL Migration Target Analysis: Java vs Rust

## Thesis

The industry standard COBOL modernization target is Java. This document
argues that Rust is a technically superior target language due to paradigm
alignment, but faces market adoption barriers. The analysis explores whether
COBOL-to-Rust represents a viable differentiated opportunity.

---

## The Paradigm Mismatch Problem

COBOL is a procedural, data-layout-aware, batch-processing language. When
migrated to Java (object-oriented, garbage-collected, enterprise), the result
is typically "COBOL-in-Java" -- classes with one giant method replicating
COBOL paragraph logic, DTOs mirroring copybook layouts byte for byte. It
compiles and runs, but it's bad Java and the business logic is obscured.

### Structural Comparison

| COBOL Concept | Rust Mapping | Java Mapping |
|---------------|-------------|-------------|
| Record layouts (copybooks) | struct with explicit field sizes | Class/DTO (verbose, no layout control) |
| REDEFINES (union types) | enum with variants (algebraic types) | No clean equivalent |
| 88-level conditions | enum variants / match patterns | Boolean methods (awkward) |
| COMP-3 packed decimal | Custom type with #[repr(packed)] | BigDecimal (works but different) |
| Procedural flow | Functions (not OOP-first) | Must force into classes |
| Fixed-point arithmetic | Explicit numeric types | BigDecimal |
| PERFORM (call paragraph) | Function call | Method call (needs a class) |
| EVALUATE TRUE | match (pattern matching) | switch (less expressive) |
| COPY member | mod / use | import (different semantics) |
| Section/paragraph structure | Modules and functions | Classes and methods (forced) |
| No garbage collection | No garbage collection | GC-managed |
| Batch processing | Iterator chains (map, filter, fold) | Streams (more ceremony) |
| Error codes / FILE STATUS | Result<T, E> (excellent fit) | Exceptions (paradigm mismatch) |
| GO TO ERROR-HANDLER | Result propagation with ? operator | throw/catch (paradigm clash) |
| PIC 9(5)V99 | Custom numeric type | BigDecimal with scale (loses intent) |

### Key Paradigm Distances

```
                COBOL
                  |
    Procedural, data-layout-aware, batch-oriented
                  |
         +--------+--------+
         |                  |
        Rust               Java
         |                  |
    Procedural-first    OOP-first
    Data-layout-aware   GC-managed
    No runtime          JVM runtime
    Pattern matching    Inheritance
    Algebraic types     Class hierarchies
    Zero-cost abstractions  Enterprise middleware

    Paradigm distance:     Paradigm distance:
    SHORT                  LONG
```

---

## Where Rust Maps Better (Technical Detail)

### 1. Copybook-to-Struct Translation

COBOL copybook:
```
01 CUSTOMER-RECORD.
   05 CUST-ID        PIC 9(8).
   05 CUST-NAME      PIC X(30).
   05 CUST-BALANCE   PIC S9(7)V99 COMP-3.
   05 CUST-STATUS    PIC X.
      88 ACTIVE      VALUE 'A'.
      88 INACTIVE    VALUE 'I'.
      88 SUSPENDED   VALUE 'S'.
```

Rust equivalent (natural):
```rust
#[repr(C)]
struct CustomerRecord {
    cust_id: [u8; 8],
    cust_name: [u8; 30],
    cust_balance: PackedDecimal<7, 2>,  // custom type
    cust_status: CustomerStatus,
}

enum CustomerStatus {
    Active,
    Inactive,
    Suspended,
}
```

Java equivalent (forced):
```java
public class CustomerRecord {
    private String custId;        // lost fixed-width semantics
    private String custName;      // lost fixed-width semantics
    private BigDecimal custBalance;
    private char custStatus;      // or enum, but 88-levels are lost

    // 50+ lines of getters, setters, constructors
    // no layout control, no packed representation
}
```

The Rust version preserves:
- Fixed-width field semantics via byte arrays
- Memory layout control via #[repr(C)]
- 88-level conditions as a proper enum (exhaustive pattern matching)
- Packed decimal as a custom type that preserves the COMP-3 intent

### 2. REDEFINES / Union Types

COBOL:
```
01 TRANSACTION-RECORD.
   05 TRANS-TYPE      PIC X.
   05 TRANS-DATA      PIC X(100).
   05 TRANS-PAYMENT REDEFINES TRANS-DATA.
      10 PAY-AMOUNT   PIC S9(9)V99 COMP-3.
      10 PAY-METHOD   PIC X(10).
   05 TRANS-REFUND  REDEFINES TRANS-DATA.
      10 REF-AMOUNT   PIC S9(9)V99 COMP-3.
      10 REF-REASON   PIC X(50).
```

Rust (natural -- algebraic types):
```rust
enum TransactionData {
    Payment { amount: PackedDecimal<9, 2>, method: [u8; 10] },
    Refund { amount: PackedDecimal<9, 2>, reason: [u8; 50] },
}
```

Java (no clean equivalent):
```java
// Option A: Inheritance hierarchy (over-engineered)
// Option B: Single class with nullable fields (error-prone)
// Option C: Separate classes with casting (verbose)
// None of these are good.
```

### 3. Batch Processing Pipelines

COBOL:
```
PERFORM UNTIL END-OF-FILE
    READ INPUT-FILE INTO WS-RECORD
    IF WS-STATUS = 'A'
        PERFORM CALCULATE-PREMIUM
        WRITE OUTPUT-RECORD FROM WS-RESULT
    END-IF
END-PERFORM
```

Rust (iterator chains):
```rust
input_reader.records()
    .filter(|r| r.status == Status::Active)
    .map(|r| calculate_premium(r))
    .for_each(|r| output_writer.write(&r).unwrap());
```

Java (streams -- similar but more ceremony):
```java
inputReader.records().stream()
    .filter(r -> r.getStatus().equals("A"))
    .map(r -> calculatePremium(r))
    .forEach(r -> outputWriter.write(r));
```

The Java version is acceptable here. The Rust version is marginally cleaner.
Both work. This is the area of least difference.

### 4. Error Handling

COBOL uses status codes and conditional flow:
```
READ INPUT-FILE
    AT END SET END-OF-FILE TO TRUE
    NOT AT END PERFORM PROCESS-RECORD
END-READ

IF FILE-STATUS NOT = '00'
    DISPLAY 'ERROR: ' FILE-STATUS
    PERFORM ERROR-HANDLER
END-IF
```

Rust (Result type -- direct mapping):
```rust
match input_file.read_record() {
    Ok(record) => process_record(record),
    Err(FileError::EndOfFile) => break,
    Err(e) => return Err(e),  // propagate with ?
}
```

Java (exceptions -- paradigm shift):
```java
try {
    Record record = inputFile.readRecord();
    processRecord(record);
} catch (EOFException e) {
    break;
} catch (IOException e) {
    handleError(e);  // or throw -- changes control flow
}
```

COBOL's error handling is value-based (check a status code, branch
accordingly). Rust's Result<T, E> with pattern matching is a direct analog.
Java's exception-based model is a fundamentally different control flow
paradigm that changes how errors propagate through the program.

---

## Why the Industry Chose Java Anyway

Despite the paradigm mismatch, Java dominates COBOL modernization (~60% of
projects) for non-technical reasons:

### 1. Developer Supply

| Language | Developers (2025) | Availability |
|----------|------------------|-------------|
| Java | 17.4 million | Easy to hire |
| Rust | 2.27 million | Hard to hire, expensive |
| COBOL | ~500-800K (declining) | The problem we're solving |

When a bank needs 50 developers to maintain the migrated system, Java wins
on pure headcount.

### 2. Enterprise Middleware Ecosystem

COBOL runs on mainframes with specific middleware. Java has equivalents:

| Mainframe Component | Java Equivalent | Rust Equivalent |
|--------------------|----------------|-----------------|
| CICS (transaction monitor) | Spring + transaction management | Nothing (no equivalent) |
| DB2 (database) | JDBC / JPA / Hibernate | SQLx / Diesel (adequate) |
| IMS (hierarchical DB) | No direct equivalent | No direct equivalent |
| MQ (messaging) | JMS / Spring AMQP / Kafka clients | AMQP / Kafka clients (adequate) |
| JCL (batch scheduling) | Spring Batch / Quartz | No equivalent framework |
| VSAM (file access method) | File I/O / database | File I/O (adequate) |

The gap is in transaction management (CICS equivalent) and batch frameworks
(JCL/Spring Batch equivalent). Rust has nothing comparable to Spring Batch
or CICS transaction management.

### 3. Commercial Vendor Lock-in

Every COBOL modernization vendor produces Java output:

| Vendor | Output Language | Market Position |
|--------|----------------|-----------------|
| AWS Mainframe Modernization | Java | Major cloud vendor |
| Micro Focus | Java / .NET | Market leader |
| Modern Systems | Java | Established |
| TSRI | Java / C# | Automated refactoring |
| IBM watsonx Code Assistant | Java | IBM ecosystem |
| Google Cloud Dual Run | Java | Google ecosystem |

**Zero vendors offer COBOL-to-Rust.** This is both the barrier and the
opportunity.

### 4. Executive Risk Tolerance

The people making migration decisions are CIOs and SVPs, not language
enthusiasts. "Migrate to Java" is a known, safe, board-approvable decision.
"Migrate to Rust" is perceived as experimental regardless of technical merit.

### 5. Regulatory Context

Financial regulators (OCC, Fed, FDIC) and auditors (Big Four) are familiar
with Java in banking environments. Rust has no track record in regulated
financial services for core processing systems. The Safety-Critical Rust
Consortium (founded June 2024) is working on this, but it targets
automotive/aerospace first, not banking.

---

## Where COBOL-to-Rust Would Win

### Batch Processing Systems

COBOL batch jobs (SORT, MERGE, sequential file processing) map naturally to
Rust iterator chains. No GC pauses mean predictable throughput. This is the
strongest use case.

### Performance-Critical Transaction Processing

If the migrated system must maintain mainframe-like throughput on commodity
hardware, Rust's zero-cost abstractions and no-GC guarantee deliver
predictable latency that Java cannot match. For payment processing, clearing
systems, or real-time risk calculation, this matters.

### Data-Intensive ETL

COBOL programs that read, transform, and write large sequential files are
essentially ETL pipelines. Rust's zero-copy parsing, memory-mapped file I/O,
and SIMD support make it a better performance target than Java for these
workloads.

### New Architecture After COBOL

If the migration is a reimplementation (not line-by-line translation), Rust
is a legitimate choice for the data processing core, with a higher-level
language (Python, TypeScript, Go) for the API layer.

---

## Market Opportunity Assessment

### Current State (2026)

- COBOL modernization market: $1.7-3.12B (2024), projected $5.3-8.59B by 2033
- COBOL-to-Java: ~60% of projects, all major vendors
- COBOL-to-Rust: 0% of projects, zero vendors
- Rust developer supply: 2.27M and growing ~40% YoY
- Safety-Critical Rust Consortium: Founded June 2024 (automotive/aerospace)

### The Gap

Nobody is building COBOL-to-Rust translation tooling. The reasons are
market-driven (developer supply, executive buy-in, vendor ecosystem), not
technical. If those market barriers erode over the next 3-5 years (as Rust
adoption grows), a first-mover in COBOL-to-Rust could differentiate in a
market where everyone else produces mediocre Java.

### Prerequisites for the Market to Open

1. Rust developer supply reaches 5M+ (projected ~2028 at current growth)
2. Safety-Critical Rust Consortium publishes financial services guidance
3. At least one major bank successfully runs Rust in production for core
   processing (not just tooling or infrastructure)
4. A credible automated translation tool exists (DARPA TRACTOR-style)
5. A systems integrator (Accenture, TCS) adds Rust to their modernization
   practice

### What Would Need to Be Built

1. **COBOL-to-Rust transpiler** -- Analogous to c2rust but for COBOL.
   Copybooks -> structs, paragraphs -> functions, 88-levels -> enums,
   REDEFINES -> algebraic types.

2. **COBOL runtime library for Rust** -- Packed decimal arithmetic, EBCDIC
   handling, indexed file access (VSAM-like), SORT/MERGE operations, report
   writer equivalent.

3. **Batch processing framework** -- Rust equivalent of Spring Batch:
   job/step/chunk model, checkpoint/restart, parallel step execution.

4. **Enterprise COBOL corpus** -- Training data for AI-assisted translation.
   This is exactly what the corpus_builder project is working toward.

---

## Conclusion

**Technical verdict**: Rust is a better paradigm match for COBOL than Java.
The translated code would be more natural, more readable, and more faithful
to the original business logic intent. The data type system (structs, enums,
pattern matching, Result) maps cleanly to COBOL concepts that Java struggles
with (REDEFINES, 88-levels, status codes, fixed-width layouts).

**Market verdict**: The market is not ready today. Java wins on developer
supply, enterprise middleware, vendor ecosystem, and executive risk tolerance.
But these are all eroding barriers, not permanent ones.

**Strategic verdict**: Building a COBOL-to-Rust capability now -- starting
with a representative COBOL corpus, a COBOL runtime library for Rust, and
a transpiler prototype -- would position for a market that doesn't exist yet
but has clear structural tailwinds. The question is whether you want to bet
on a 3-5 year horizon or focus on what the market is buying today.

---

## Key References

COBOL modernization market:
- Dataintelo: COBOL Modernization Services Market
- GAO-25-107795: Federal Legacy Systems Modernization

Rust adoption:
- JetBrains DevEco 2024: Rust developer count (2.27M)
- SlashData 2025: Global developer population
- GitHub Octoverse 2023: Rust 40% YoY growth

Safety-Critical Rust:
- Rust Foundation: Safety-Critical Rust Consortium (June 2024)
  https://rustfoundation.org/media/announcing-the-safety-critical-rust-consortium/
- Ferrocene: ISO 26262 ASIL-D qualified Rust compiler
  https://ferrous-systems.com/ferrocene

COBOL-to-Java vendors:
- AWS Mainframe Modernization
- IBM watsonx Code Assistant for Z
- Micro Focus Enterprise Suite
- Google Cloud Mainframe Modernization

DARPA TRACTOR (C-to-Rust, analogous approach):
- https://www.darpa.mil/research/programs/translating-all-c-to-rust

Related project documentation:
- docs/c_to_rust_modernization.md -- C/C++ to Rust reference material
- docs/c_to_rust_market_assessment.md -- Market sizing
- docs/darpa_tractor_deep_dive.md -- DARPA program analysis
- docs/java_migration_business_case.md -- Java 8 -> 17/21 analysis
- docs/foia_request_template.md -- Federal COBOL source code request


# Current C to Rust migration code bases
https://github.com/immunant/c2rust
https://github.com/DARPA-TRACTOR-Program/PUBLIC-Test-Corpus/tree/main
