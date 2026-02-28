# Legacy Java (8/11) to Modern Java (17/21+): Business Case

## Short Answer

Yes, there is a strong business case -- and it is arguably the most
actionable modernization opportunity today because:

1. The tooling is mature (OpenRewrite, Amazon Q Developer)
2. The forcing functions are immediate (Oracle licensing, Spring Boot EOL)
3. The performance gains are measurable (8-15% throughput, 10%+ infra savings)
4. The code is accessible (unlike COBOL mainframes or C embedded firmware)

---

## The Scale

### Java Version Distribution in Production (2024)

| Version | Share | Trend |
|---------|-------|-------|
| Java 17 | ~35% | Now #1, surged ~300% YoY |
| Java 11 | ~33% | Declining |
| Java 8 | <30% | Declining (was dominant for years) |
| Java 21 | ~1.4% | Early but 287% faster adoption than Java 17 |

Source: New Relic 2024 State of the Java Ecosystem
https://newrelic.com/resources/report/2024-state-of-the-java-ecosystem

**Key finding**: Java 17 overtook Java 8 and 11 as the #1 production version
in 2024. The tipping point has passed, but ~63% of production Java is still
on older versions -- representing millions of applications that need upgrading.

### Developer Population

- Java developers: ~17.4 million globally (SlashData 2025)
- Java remains the #3 most popular language (TIOBE Feb 2025: 10.56%)

---

## Three Forcing Functions

### 1. Oracle Licensing (Financial Pressure)

Oracle's January 2023 shift to "Java SE Universal Subscription":

- Per-employee pricing: $5.25-$15/employee/month
- "Employee" = everyone in the org, whether they use Java or not
- Real costs: 500 employees = ~$90K/year; 5,000 = ~$630K/year
- Companies report 500-700% cost increases
- 88% of enterprises considering migrating off Oracle Java (Azul 2025)

Migrating to OpenJDK (free) practically requires upgrading from Java 8
since free Oracle Java 8 public updates ended January 2019.

Sources:
- https://www.azul.com/newsroom/azul-2025-state-of-java-survey-report/
- https://oraclelicensingexperts.com/oracle-java-licensing-costs-increase-by-700/

### 2. Spring Boot 2.x End of Life (Security Pressure)

- Spring Boot 2.x community support: ended November 2023
- Spring Boot 2.x commercial support: ended August 2025
- After that: no security patches for Spring Boot or managed dependencies
- Spring Boot 3.x requires Java 17+ and jakarta namespace

This is the single most common framework in enterprise Java. Its EOL forces
a triple migration: Java version + javax->jakarta + Spring Boot 2->3.

Sources:
- https://endoflife.date/spring-boot
- https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide

### 3. Cloud Provider Deprecations (Infrastructure Pressure)

- AWS Lambda: AL2-based runtimes for Java 8/11/17 migrating to AL2023 by Q2 2026
- Java 8 on AL1: already unsupported since Jan 2024
- Azure/GCP: following similar upstream EOL alignment

---

## The Triple Migration Problem

This is the critical insight: you cannot upgrade one without the others.

```
Spring Boot 2.x (EOL)          Spring Boot 3.x (current)
  |                               |
  +-- Java 8-17                   +-- Java 17+ REQUIRED
  +-- javax.* namespace           +-- jakarta.* namespace REQUIRED
  +-- Tomcat 9 / Jetty 9          +-- Tomcat 10+ / Jetty 11+
  +-- Hibernate 5.x               +-- Hibernate 6.x
  +-- Spring Security 5.x         +-- Spring Security 6.x
```

What breaks:
- Every javax.servlet, javax.persistence, javax.validation import
- Removed JDK APIs: JAXB (javax.xml.bind), JAX-WS, CORBA, Nashorn
- Strong encapsulation of JDK internals (sun.*, com.sun.*)
- Third-party libraries must also release Jakarta-compatible versions
- Application servers must be upgraded (Tomcat 9 -> 10+, Jetty 9 -> 11+)

---

## Migration Tooling (Mature)

| Tool | Maturity | Type | Best For |
|------|----------|------|----------|
| OpenRewrite/Moderne | HIGH | Deterministic automated | Enterprise-scale, multi-repo |
| Amazon Q Developer | HIGH | AI-assisted | AWS teams, Spring Boot apps |
| jdeps/jdeprscan | HIGH | Diagnostics | Pre-migration assessment |
| IntelliJ IDEA | HIGH | Interactive | Single-project developer work |

### OpenRewrite (Most Comprehensive)

Open-source automated refactoring engine. Recipes for:
- Java 8 -> 11 -> 17 -> 21 -> 25 version migration
- Spring Boot 2.x -> 3.x
- javax -> jakarta namespace
- Hibernate, Spring Cloud, Elasticsearch migrations
- Deterministic (not AI-based) -- predictable results

https://docs.openrewrite.org/recipes/java/migrate

### Amazon Q Developer (Best-Documented Results)

Amazon internally upgraded 1,000 production apps from Java 8 to 17 in 2
days with a 5-person team. Average: 10 minutes per application. 79% of
auto-generated code reviews accepted without changes.

https://aws.amazon.com/q/developer/transform/

---

## Performance Gains

### Java 8 -> Java 17

- OptaPlanner/Timefold: 8.66% faster than Java 11
- General throughput: ~15% improvement over Java 11
- GC time: ~20% reduction (G1 improvements)
- No code changes required -- just upgrade the JVM

Source: https://www.optaplanner.org/blog/2021/09/15/HowMuchFasterIsJava17.html

### Java 17 -> Java 21

- General throughput: ~12% faster
- Generational ZGC: 10% throughput improvement, 75% memory reduction
- GC pause times: sub-millisecond with ZGC
- Virtual threads: millions of concurrent lightweight threads for I/O
- Halodoc: ~30% heap reduction, >10% infrastructure cost reduction

Sources:
- https://kstefanj.github.io/2023/12/13/jdk-21-the-gcs-keep-getting-better.html
- https://blogs.halodoc.io/migrating-from-jdk-17-to-jdk-21-an-overview-and-practical-guide/

---

## Market Size

| Market | Size | Source |
|--------|------|--------|
| Application Modernization Services | $19.82B (2024) -> $39.62B (2029) | MarketsandMarkets |
| Java Development Services | $9.83B (2024) -> $16.25B (2032) | Future Market Report |
| Legacy Software Modernization | $15.14B (2025) -> $27.3B (2029) | Research and Markets |
| COBOL Modernization (comparison) | $1.7-3.12B (2024) | Dataintelo |

**Java-specific migration market**: Not separately tracked by any analyst.
Estimated $2-5B annually based on subset of app modernization market.

---

## Enterprise Adoption Stories

| Organization | Migration | Result |
|-------------|-----------|--------|
| Amazon | 1,000 apps Java 8 -> 17 | 2 days, 5-person team, 79% auto-accepted |
| Very Good Security | Java 8 -> 17 | 50% reduction in long requests (>400ms) |
| Halodoc | Java 17 -> 21 | 30% heap reduction, >10% infra cost savings |

---

## Comparison to Other Modernization Opportunities

| Factor | COBOL | C/C++ to Rust | Java 8 -> 17/21 |
|--------|-------|---------------|-----------------|
| Code accessibility | Behind mainframe firewalls | Everywhere but embedded | Everywhere |
| Tooling maturity | Multiple commercial vendors | Early (c2rust only) | Mature (OpenRewrite, Q) |
| Migration complexity | Extreme (language change) | Extreme (ownership model) | Moderate (same language) |
| Forcing function | Talent extinction | Security mandates | Licensing + framework EOL |
| Automation potential | Medium | Low-Medium | HIGH (79% auto-acceptance) |
| Market size | $1.7-3.12B | Est. $5-15B | Est. $2-5B |
| Time to value | Years | Years | Weeks to months |

---

## Why This Matters for Corpus Building

Java migration is fundamentally different from COBOL or C-to-Rust:

1. **Same language**: Java 8 -> Java 21 is the same language with API changes,
   not a language translation problem. This means AST-level tooling (like
   OpenRewrite) can handle most transformations deterministically.

2. **Code is abundant**: Unlike COBOL, there are millions of open-source Java
   projects on GitHub running on Java 8/11. A "Java modernization corpus"
   would be trivially easy to build.

3. **Before/after pairs exist**: OpenRewrite generates diffs. Amazon Q generates
   diffs. These before/after transformation pairs are ideal training data for
   AI-assisted migration tools.

4. **The market is ready**: Companies are actively spending money to migrate
   right now (Spring Boot 2.x EOL was August 2025). Timing is immediate.

5. **Lower barrier**: Building an evaluation tool for Java repos (similar to
   your COBOL evaluate command) would be straightforward -- scc already
   recognizes Java, and version detection can be done from pom.xml/build.gradle.

---

## Key URLs

Surveys and Reports:
- New Relic 2024: https://newrelic.com/resources/report/2024-state-of-the-java-ecosystem
- Azul 2025: https://www.azul.com/newsroom/azul-2025-state-of-java-survey-report/
- Adoptium stats: https://blogs.eclipse.org/post/carmen-delgado/adoptium-2025-year-momentum-innovation-and-trust-open-source-java-runtimes

Oracle Licensing:
- Price list: https://www.oracle.com/a/ocom/docs/corporate/pricing/java-se-subscription-pricelist-5028356.pdf
- Cost analysis: https://oraclelicensingexperts.com/oracle-java-licensing-costs-increase-by-700/

Migration Tooling:
- OpenRewrite: https://docs.openrewrite.org/recipes/java/migrate
- Moderne: https://www.moderne.ai
- Amazon Q: https://aws.amazon.com/q/developer/transform/
- Spring Boot 3 Guide: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide

Performance:
- Java 17 benchmarks: https://www.optaplanner.org/blog/2021/09/15/HowMuchFasterIsJava17.html
- Java 21 GC: https://kstefanj.github.io/2023/12/13/jdk-21-the-gcs-keep-getting-better.html
- Halodoc case study: https://blogs.halodoc.io/migrating-from-jdk-17-to-jdk-21-an-overview-and-practical-guide/
