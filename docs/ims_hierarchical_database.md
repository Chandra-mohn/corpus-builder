# IBM IMS (Information Management System)

## Overview

IMS is IBM's hierarchical database and transaction manager, first deployed
in 1966 to track parts for the Saturn V rocket during the Apollo program.
It is one of the oldest pieces of software still in active production
anywhere in the world.

IBM reports IMS processes **50+ billion transactions per day** across its
installed base -- more than all the world's web APIs combined.

---

## How Hierarchical Databases Work

Unlike relational databases (tables with rows/columns and SQL joins), IMS
organizes data as **trees**:

```
                    CUSTOMER
                   /        \
              ORDER-1      ORDER-2
             /   |   \        |
          ITEM-1 ITEM-2 ITEM-3  ITEM-4
```

- Each record type is a **segment**
- Segments are connected in parent-child relationships
- The topmost segment is the **root**
- Navigation is by traversing the tree: "get the next child of this parent"
- There are no JOINs -- relationships are physical, not logical
- Access is via **DL/I calls** (Data Language/Interface), not SQL

### Key Concepts

| IMS Term | Relational Equivalent | Description |
|----------|----------------------|-------------|
| Segment | Row (roughly) | A record in the hierarchy |
| Segment type | Table (roughly) | Definition of a record structure |
| Root segment | Parent table | Topmost record in the hierarchy |
| Database Description (DBD) | Schema | Defines the hierarchy structure |
| Program Communication Block (PCB) | View | A program's view of the database |
| Program Specification Block (PSB) | Permission set | Collection of PCBs for a program |
| Segment Search Argument (SSA) | WHERE clause | Navigation criteria |

---

## DL/I Calls: How COBOL Talks to IMS

COBOL programs access IMS through DL/I calls embedded in the code:

```cobol
CALL 'CBLTDLI' USING GU-FUNCTION
                     CUSTOMER-PCB
                     CUSTOMER-IO-AREA
                     SSA-CUSTOMER-KEY.
```

### DL/I Operations

| Call | Full Name | Meaning | Relational Equivalent |
|------|-----------|---------|----------------------|
| GU | Get Unique | Random access by key | SELECT WHERE key = ? |
| GN | Get Next | Sequential forward | Cursor FETCH NEXT |
| GNP | Get Next within Parent | Next child of current parent | SELECT WHERE parent_id = ? (next) |
| GHU | Get Hold Unique | Lock for update by key | SELECT FOR UPDATE WHERE key = ? |
| GHN | Get Hold Next | Lock next for update | FETCH NEXT FOR UPDATE |
| GHNP | Get Hold Next within Parent | Lock next child for update | FETCH NEXT child FOR UPDATE |
| ISRT | Insert | Add a segment | INSERT |
| DLET | Delete | Remove a segment | DELETE |
| REPL | Replace | Update a segment | UPDATE |
| CHKP | Checkpoint | Save recovery point | COMMIT (partial) |
| ROLB | Rollback | Undo to last checkpoint | ROLLBACK |

There is no query language. Every database access is a **navigational call**
-- the programmer tells the database exactly which path to walk through the
tree. The programmer IS the query optimizer.

### SSA (Segment Search Arguments)

SSAs tell IMS which segments to find. They come in two forms:

**Unqualified SSA** (just the segment name):
```cobol
01 UNQUAL-SSA.
   05 SEG-NAME    PIC X(8) VALUE 'CUSTOMER'.
   05 FILLER      PIC X    VALUE ' '.
```

**Qualified SSA** (segment name + key criteria):
```cobol
01 QUAL-SSA.
   05 SEG-NAME    PIC X(8)  VALUE 'CUSTOMER'.
   05 FILLER      PIC X     VALUE '('.
   05 KEY-NAME    PIC X(8)  VALUE 'CUSTKEY '.
   05 REL-OP      PIC X(2)  VALUE ' ='.
   05 KEY-VALUE   PIC X(10) VALUE '0000012345'.
   05 FILLER      PIC X     VALUE ')'.
```

This is essentially a hardcoded query plan. There is no optimizer that
can rearrange access paths -- what the programmer wrote is what executes.

---

## IMS Architecture

```
+------------------+
|  COBOL Program   |  <-- application code with DL/I calls
+------------------+
         |
    DL/I interface
         |
+------------------+
|  IMS TM          |  <-- transaction manager
|  (IMS DC)        |      - message queues
|                  |      - scheduling
|                  |      - security
|                  |      - recovery
+------------------+
         |
+------------------+
|  IMS DB          |  <-- database manager
|                  |      - hierarchical access
|                  |      - segment retrieval
|                  |      - index management
+------------------+
         |
+------------------+
|  VSAM / OSAM     |  <-- physical storage
|  (z/OS datasets) |      - VSAM: Virtual Storage Access Method
|                  |      - OSAM: Overflow Sequential Access Method
+------------------+
```

### Two Components in One

IMS is actually two products:

**IMS DB (Database Manager)**: The hierarchical database engine. Manages
segment storage, retrieval, indexing, and access path optimization.

**IMS TM (Transaction Manager)**: Like CICS but for IMS. Handles online
transaction processing with:
- Message queues (input/output)
- Transaction scheduling and priority
- Security (RACF integration)
- Logging and recovery
- Conversational and non-conversational modes
- Parallel processing regions (MPPs, BMPs)

Programs can be:
- **MPP (Message Processing Program)**: Online, processes one transaction
  at a time from the message queue
- **BMP (Batch Message Processing)**: Batch programs that can also access
  IMS databases and message queues
- **DL/I Batch**: Pure batch programs that access IMS databases only

---

## Database Organization Types

IMS supports several physical storage organizations:

| Type | Full Name | Description | Use Case |
|------|-----------|-------------|----------|
| HISAM | Hierarchical Indexed Sequential | Indexed access, sequential overflow | Small databases, mixed access |
| HIDAM | Hierarchical Indexed Direct | Index + direct storage | Large databases, random access |
| HDAM | Hierarchical Direct Access | Hash-based direct access | High-volume random access |
| HSAM | Hierarchical Sequential | Pure sequential | Batch processing, archives |
| DEDB | Data Entry Database | Fast Path, high-volume | Ultra-high-volume transactions |
| MSDB | Main Storage Database | In-memory | Real-time lookup data |

### Secondary Indexes

IMS supports secondary indexes that allow access to segments by non-key
fields. This partially bridges the gap to relational-style access but
within the hierarchical model:

```
Primary path:  CUSTOMER -> ORDER -> ITEM
Secondary:     INDEX(ORDER-DATE) -> ORDER -> CUSTOMER (inverted)
```

### Logical Relationships

IMS allows "logical relationships" between segments in different databases,
creating a network-like structure on top of the hierarchy:

```
Database A:              Database B:
CUSTOMER                 PRODUCT
   |                        |
   ORDER ---- logical ---> ORDER-PRODUCT (virtual)
   |
   ITEM
```

This is one of the most complex IMS features and one of the hardest to
migrate -- it creates cross-database joins without SQL.

---

## Who Uses IMS

IMS is concentrated in the largest, oldest enterprises:

### Banking and Financial Services
- Core account processing
- Payment clearing and settlement
- ATM transaction processing
- Wire transfer systems
- Credit card authorization
- Major users: JPMorgan Chase, Bank of America, Wells Fargo, Citibank

### Insurance
- Policy management
- Claims processing
- Underwriting systems

### Government
- IRS: Tax processing systems
- SSA: Benefits processing
- DOD: Logistics and personnel systems
- Some of the largest IMS installations in the world

### Airlines and Travel
- Reservation systems (though many have migrated)
- Historical systems still running at some carriers

### Healthcare
- Hospital systems
- Insurance claims processing

---

## Why IMS Migration Is the Hardest Problem

IMS is the single hardest component to modernize in any mainframe stack.
Here's why:

### 1. No Modern Equivalent Exists

Hierarchical databases were replaced by relational databases (1980s onward)
for good reasons. But IMS programs are designed around navigational access
patterns that assume hierarchical structure. You cannot swap in PostgreSQL
without rethinking the entire data access layer.

### 2. Data and Logic Are Intertwined

COBOL programs contain explicit navigation logic:
```cobol
* Get the customer
CALL 'CBLTDLI' USING GU CUST-PCB CUST-AREA CUST-SSA.
* Get first order for this customer
CALL 'CBLTDLI' USING GNP CUST-PCB ORDER-AREA ORDER-SSA.
* Get all items for this order
PERFORM UNTIL STATUS-CODE = 'GE'
    CALL 'CBLTDLI' USING GNP CUST-PCB ITEM-AREA ITEM-SSA
END-PERFORM.
```

This tree-walking logic has no SQL equivalent. Converting to SQL requires:
- Flattening the hierarchy into tables
- Replacing navigational calls with set-based queries
- Rethinking the entire program flow

### 3. Positional vs Set-Based Access

IMS navigation is **positional**: "I'm at this segment; get me the next one."
SQL is **set-based**: "Give me all records matching this criteria."

These are fundamentally different programming paradigms. A COBOL program
that processes records sequentially with GN/GNP calls must be restructured
to use cursors, result sets, or collection-based processing.

### 4. PCB Views

Multiple IMS programs may share the same IMS database with different
**views** (PCBs). Each program sees a different subset of the hierarchy.
Program A might see:
```
CUSTOMER -> ORDER -> ITEM
```
While Program B sees:
```
CUSTOMER -> ORDER -> SHIPMENT
```

Replicating this in a relational model requires careful view/permission
design with different SQL views and role-based access.

### 5. Transaction Semantics

IMS TM has specific commit/rollback, checkpoint, and message queue semantics:
- Single-phase commit within IMS
- Sync point coordination with external resources
- Message queue persistence and recovery
- Conversational transaction state preservation

These don't map directly to modern transaction managers or message brokers.

### 6. Performance at Scale

IMS is extremely fast for its designed access patterns. Tree traversal
with known paths is O(depth), not O(n). The same queries expressed as SQL
joins can be orders of magnitude slower if the relational schema isn't
designed to match the original access patterns.

---

## Modern IMS (IBM's Strategy)

IBM hasn't abandoned IMS. They actively develop it:

### IMS 15.4 (Current Release)
- Java API support (IMS Universal drivers)
- REST API gateway (IMS Connect)
- JSON input/output support
- XML support
- JDBC access to IMS databases (read/write)
- Open Database (ODBM) for distributed access

### Integration Points
- **IMS Connect**: TCP/IP gateway allowing modern apps to call IMS transactions
- **IMS Open Database**: JDBC/SQL access to IMS hierarchical data
- **IMS Mobile Feature Pack**: REST APIs for mobile applications
- **IMS Explorer**: Eclipse-based GUI for IMS administration
- **z/OS Connect EE**: API management layer over IMS

### IBM's Approach

IBM's strategy is NOT to replace IMS but to **wrap it**:

```
+------------------+
| Modern APIs      |  <-- REST, JSON, GraphQL
| (z/OS Connect)   |
+------------------+
         |
+------------------+
| IMS Connect      |  <-- TCP/IP gateway
+------------------+
         |
+------------------+
| IMS TM + DB      |  <-- same COBOL + DL/I, unchanged
+------------------+
```

This is pragmatic: the COBOL/DL/I code inside stays forever, but it becomes
accessible from modern applications. The business logic doesn't change;
the interface does.

---

## IMS Migration Approaches

When organizations do attempt IMS migration, there are several approaches:

### 1. Data Model Transformation (Full Migration)

Flatten the IMS hierarchy into relational tables:

```
IMS:                    Relational:
CUSTOMER                customer (table)
   |                    order (table, FK -> customer)
   ORDER                item (table, FK -> order)
   |
   ITEM
```

Then rewrite all DL/I calls as SQL. This is the most complete but most
expensive approach.

### 2. Hierarchical-to-Document Mapping

Map IMS hierarchies to document databases (MongoDB, Couchbase):

```
IMS Hierarchy    ->    MongoDB Document
CUSTOMER               {
   |                      customer_id: "12345",
   ORDER                  orders: [
   |                        {
   ITEM                       order_id: "001",
                              items: [...]
                            }
                          ]
                        }
```

This preserves the hierarchical structure but moves to modern infrastructure.
The DL/I navigational access patterns map somewhat more naturally to document
database traversal than to SQL.

### 3. API Wrapping (IBM's Approach)

Leave IMS in place. Expose IMS transactions as REST APIs via IMS Connect
and z/OS Connect. New applications call the APIs; old COBOL programs
continue running unchanged.

This avoids migration risk but perpetuates the mainframe dependency.

### 4. Event Sourcing / CQRS

Treat IMS transactions as events. Replicate IMS data changes to a modern
event store (Kafka). Build read models on modern databases. Gradually
shift write operations to new services.

This is the most architecturally sophisticated approach and the most
expensive.

### 5. Graph Database Migration (Best Paradigm Fit)

Graph databases are the **closest modern paradigm** to IMS's hierarchical/
navigational model. IMS's two hardest migration problems -- logical
relationships and navigational access -- are exactly what graph databases
do best.

#### Why Graph Databases Map Well to IMS

| IMS Concept | Graph Equivalent | Fit |
|-------------|-----------------|-----|
| Segment | Node (vertex) | Direct mapping |
| Parent-child relationship | Edge (directed) | Direct mapping |
| Root segment | Entry point node | Direct mapping |
| Logical relationship | Cross-database edge | Better than IMS -- graphs handle this natively |
| Secondary index | Index on node properties | Standard feature |
| DL/I GU (Get Unique) | Node lookup by property | Direct mapping |
| DL/I GN (Get Next) | Traverse next edge | Direct mapping |
| DL/I GNP (Get Next in Parent) | Traverse child edges | Direct mapping |
| SSA (navigation criteria) | Pattern matching in query | More expressive |
| PCB views | Subgraph projections | More flexible |

#### DL/I to Cypher Translation

A realistic IMS program flow translated to Neo4j Cypher:

```cobol
* COBOL/IMS: Get customer, all orders, and items for each order
CALL 'CBLTDLI' USING GU CUST-PCB CUST-AREA CUST-SSA.
IF PCB-STATUS = SPACES
    PERFORM UNTIL PCB-STATUS = 'GE'
        CALL 'CBLTDLI' USING GNP CUST-PCB ORDER-AREA ORDER-SSA
        IF PCB-STATUS = SPACES
            PERFORM UNTIL PCB-STATUS = 'GE'
                CALL 'CBLTDLI' USING GNP CUST-PCB ITEM-AREA ITEM-SSA
                IF PCB-STATUS = SPACES
                    PERFORM PROCESS-ITEM
                END-IF
            END-PERFORM
        END-IF
    END-PERFORM
END-IF.
```

```cypher
// Cypher equivalent: one query replaces 20+ lines of navigational code
MATCH (c:Customer {id: $custId})-[:HAS_ORDER]->(o)-[:HAS_ITEM]->(i)
RETURN c, o, i
ORDER BY o.order_date, i.item_seq
```

The entire nested loop structure with status code checking collapses to a
single declarative query.

#### Logical Relationships Become Trivial

IMS logical relationships (cross-database joins) -- one of the hardest
migration problems -- are just edges in a graph:

```
IMS:                          Graph:
Database A:  CUSTOMER         (Customer)-[:PLACED]->(Order)
Database B:  PRODUCT          (Order)-[:CONTAINS]->(Product)
Logical rel: ORDER-PRODUCT    // no special construct needed -- just edges
```

#### Graph Database Options

| Database | Query Language | Enterprise Ready? | Best For |
|----------|---------------|-------------------|----------|
| Neo4j | Cypher | Yes (enterprise edition) | Most mature, largest community |
| Amazon Neptune | Gremlin, SPARQL, openCypher | Yes (managed AWS) | AWS shops |
| Azure Cosmos DB | Gremlin | Yes (managed Azure) | Azure shops, multi-model |
| TigerGraph | GSQL | Yes | High-performance analytics |
| JanusGraph | Gremlin | Yes (open-source) | Distributed, scalable |
| ArangoDB | AQL | Yes | Multi-model (graph + document + KV) |
| Memgraph | Cypher | Yes | In-memory, real-time |
| SurrealDB | SurrealQL | Emerging | Multi-model, Rust-based |

#### Barriers to Graph Database Migration

1. **Transaction processing scale**: IMS handles 50+ billion transactions/day.
   Graph databases are not proven at that scale for OLTP workloads.

   | System | Proven Transaction Scale |
   |--------|------------------------|
   | IMS | 50+ billion/day |
   | Neo4j | Millions/day (enterprise) |
   | Neptune | Millions/day |
   | TigerGraph | Billions/day (analytics, not OLTP) |

2. **No bank has done it**: Graph databases are used in banking for fraud
   detection and KYC/AML, but NOT for core account processing, payment
   clearing, or settlement -- which is where IMS lives.

3. **Batch processing gap**: IMS batch (BMP, DL/I batch) processes millions
   of records sequentially. Graph databases are optimized for traversal,
   not bulk sequential processing.

4. **COBOL translation still required**: Even with graph DB as the target
   data store, the COBOL business logic still needs translation to another
   language (Rust, Java, etc.).

#### Practical Hybrid Architecture

The most realistic IMS migration using graph databases would be hybrid:

```
+------------------+
| API Layer        |  <-- REST/GraphQL (any language)
+------------------+
         |
+------------------+
| Business Logic   |  <-- Rust or Java (translated from COBOL)
+------------------+
    |            |
+--------+  +--------+
| Graph  |  | RDBMS  |
| DB     |  |        |
| (Neo4j)|  | (Pg)   |
+--------+  +--------+
    |            |
 Navigational  Bulk/batch
 queries       processing
```

- Graph database for navigational/hierarchical queries (customer -> orders
  -> items) -- where IMS's strength lives
- Relational database for bulk batch processing, reporting, and flat queries
- Business logic in Rust or Java, translated from COBOL

---

## Modern Tree/Hierarchical Database Alternatives

While no mainstream modern database replicates IMS's exact hierarchical
model, tree-structured data lives in different packaging today:

### Document Databases (Closest Modern Equivalent)

| Database | How It Works |
|----------|-------------|
| MongoDB | Documents ARE trees -- nested objects/arrays map to segments |
| Couchbase | Same as MongoDB -- JSON documents with arbitrary depth |
| Firebase Realtime DB | Literally a JSON tree -- closest conceptual match to IMS |
| Azure Cosmos DB | Multi-model, document mode supports hierarchical structures |

Firebase is actually the most IMS-like modern database. Its data model is
a single JSON tree, and you navigate by path:

```
IMS:      GU CUSTOMER(CUSTKEY='123') / GNP ORDER
Firebase: ref('customers/123/orders').orderByKey().limitToFirst(1)
```

### XML Databases (Explicitly Hierarchical)

| Database | Status | Notes |
|----------|--------|-------|
| MarkLogic | Active, enterprise | XML/JSON document store, XQuery |
| eXist-db | Active, open-source | Native XML database, XPath/XQuery |
| BaseX | Active, open-source | XML database, full XQuery support |

XPath is a tree navigation language that maps to DL/I:

```
DL/I:   GU CUSTOMER(CUSTKEY='123') / GNP ORDER / GNP ITEM
XPath:  /customer[@id='123']/order[1]/item
```

But XML databases never achieved mainstream adoption for transactional
workloads.

### Relational Databases with Tree Support

| Feature | Available In | Description |
|---------|-------------|-------------|
| Recursive CTEs | PostgreSQL, Oracle, SQL Server, MySQL 8+ | Walk parent-child trees with SQL |
| CONNECT BY | Oracle | Hierarchical queries (proprietary, since 1980s) |
| ltree | PostgreSQL extension | Materialized path labels for tree structures |
| JSON columns | All modern RDBMS | Store nested hierarchies in JSON columns |
| Nested Sets | Pattern (any RDBMS) | Encode tree position for fast subtree queries |

---

## IMS and the Corpus Builder

### Detecting IMS Code

IMS-heavy COBOL programs can be detected by:

- DL/I call patterns: `CALL 'CBLTDLI'` or `CALL 'PLITDLI'`
- PCB declarations in the PROCEDURE DIVISION USING clause
- SSA definitions in WORKING-STORAGE
- IMS status code checking: `IF PCB-STATUS = 'GE'`
- PSB includes/references

The corpus_builder dialect detector (`extract/dialect.py`) already detects
IMS dialect via DL/I patterns.

### Value of IMS COBOL Code

IMS-heavy COBOL is the **most valuable and hardest-to-find** code for
modernization research because:

1. It represents the most complex migration scenarios
2. It's concentrated in the most security-conscious organizations
3. It's the code that commercial modernization vendors struggle with most
4. No open-source IMS COBOL examples of realistic complexity exist
5. IBM provides trivial samples but not enterprise-grade examples

### Rust Mapping Potential

IMS hierarchical structures map to Rust concepts:

| IMS Concept | Rust Mapping |
|-------------|-------------|
| Segment hierarchy | Nested structs / enum variants |
| Parent-child relationship | Vec<ChildSegment> field on parent |
| Logical relationship | References (Box, Rc, Arc) |
| SSA navigation | Iterator-based tree traversal |
| DL/I GN/GNP | Iterator::next() / children().next() |
| DL/I GU | HashMap lookup or tree search |
| PCB views | Trait-based views over data structures |
| Status codes | Result<Segment, ImsError> |

This is conceptually interesting but nobody is working on IMS-to-Rust
migration tooling. The IMS installed base runs on z/OS mainframes at the
most conservative organizations in the world.

---

## Key References

IBM IMS Documentation:
- IMS 15.4 Knowledge Center: https://www.ibm.com/docs/en/ims
- IMS Product Page: https://www.ibm.com/products/ims

IMS Architecture:
- DL/I Reference: https://www.ibm.com/docs/en/ims/15.4?topic=reference-dli-calls
- Database Description (DBD): https://www.ibm.com/docs/en/ims/15.4?topic=utilities-database-description-generation

IMS Modernization:
- IMS Connect: https://www.ibm.com/docs/en/ims/15.4?topic=connect-ims-overview
- z/OS Connect EE: https://www.ibm.com/docs/en/zosconnect
- IMS Open Database: https://www.ibm.com/docs/en/ims/15.4?topic=open-database-ims

Related project documentation:
- docs/cobol_migration_target_analysis.md -- COBOL -> Java vs Rust analysis
- corpus_builder/extract/dialect.py -- IMS dialect detection
