# FOIA Request Template -- Federal COBOL Source Code for Modernization Research

**Note:** This is a template. Fill in [BRACKETED ITEMS] before submitting.
You should submit separate letters to each target agency.

---

## Target Agencies

| Agency | FOIA Office | Submission |
|--------|-------------|------------|
| SSA (Social Security Administration) | Office of Privacy and Disclosure, 6401 Security Blvd, Baltimore MD 21235 | Online: https://foia.ssa.gov/app/Home.aspx |
| Treasury / IRS | IRS FOIA Request, HQ FOIA, Stop 211, PO Box 621506, Atlanta GA 30362-3006 | Online: https://www.irs.gov/privacy-disclosure/irs-freedom-of-information |
| VA (Veterans Affairs) | Department of Veterans Affairs, FOIA Service (005R1C), 810 Vermont Ave NW, Washington DC 20420 | Online: https://www.va.gov/foia/ |
| OPM (Office of Personnel Management) | FOIA Requester Service Center, 1900 E Street NW, Room 5415, Washington DC 20415 | Email: foia@opm.gov |

---

## Letter

[YOUR NAME]
[YOUR ADDRESS]
[YOUR EMAIL]
[YOUR PHONE]

[DATE]

Freedom of Information Officer
[AGENCY NAME]
[AGENCY FOIA ADDRESS]

**Re: Freedom of Information Act Request -- Legacy COBOL Source Code
for Modernization Research**

Dear FOIA Officer:

Pursuant to the Freedom of Information Act (FOIA), 5 U.S.C. 552, I am
requesting access to COBOL source code, copybook libraries, and Job
Control Language (JCL) procedures maintained by [AGENCY NAME] for the
purpose of academic and applied research into legacy software
modernization.

### Background and Public Interest

The Government Accountability Office has repeatedly identified federal
legacy COBOL systems as a critical modernization priority. Most
recently, GAO-25-107795 ("Information Technology: Agencies Need to Plan
for Modernizing Critical Decades-Old Legacy Systems," July 2025) found
that 8 of 11 critical federal legacy systems use outdated languages,
with a shrinking pool of qualified developers.

Effective modernization tooling -- including automated code analysis,
migration planning, and AI-assisted translation -- requires
representative enterprise COBOL source code for development and
validation. Currently, no publicly available corpus of enterprise-grade
COBOL exists. Publicly available COBOL code on platforms like GitHub
consists overwhelmingly of educational samples and vendor
demonstrations, which do not reflect the structural complexity of
production federal systems.

Access to representative federal COBOL source code would directly
support:

  - Development of open-source modernization tools available to all
    federal agencies
  - Training data for AI-assisted code analysis and migration systems
  - Academic research into legacy software patterns and technical debt
  - Benchmarking of commercial modernization offerings used by federal
    agencies

### Specific Records Requested

To minimize the scope of this request and reduce the likelihood of
material requiring redaction, I am specifically requesting:

1. **COBOL copybook libraries (COPY members):** Data structure
   definitions used across programs. These define record layouts and
   are structural rather than procedural -- they contain no business
   logic, security algorithms, or fraud detection routines.

2. **JCL procedure libraries (PROCLIBs):** Job Control Language
   procedures that define batch job execution sequences. These describe
   operational workflows but do not contain application logic.

3. **COBOL source programs from any system that has been decommissioned
   or fully replaced:** Source code from systems no longer in
   production use poses no security risk, as the code no longer
   controls any active process.

4. **COBOL source programs from any system for which the agency has
   published modernization completion:** Per GAO-25-107795, several
   agencies have completed modernization of legacy systems. The
   replaced COBOL code from these completed modernizations is no longer
   operationally sensitive.

I am **not** requesting:

  - Source code for active fraud detection, security authentication, or
    access control systems
  - Database contents, personally identifiable information, or
    production data
  - Proprietary software licensed from third-party vendors
  - Source code for systems currently under active security review

### Fee Waiver Request

I request a waiver of all fees associated with this request pursuant to
5 U.S.C. 552(a)(4)(A)(iii). Disclosure of this information is in the
public interest because:

1. The requested records concern federal government operations and
   activities -- specifically, the structure and design of taxpayer-
   funded information systems.

2. Disclosure will significantly contribute to public understanding of
   how federal legacy systems are structured, informing the public
   debate on modernization priorities and spending.

3. The requester has the ability and intent to disseminate the
   information broadly as part of an open-source research dataset
   available to researchers, federal contractors, and other government
   agencies.

4. The request is not primarily in the commercial interest of the
   requester. The resulting dataset will be released under an open
   license for public benefit.

### Legal Basis

Works authored by federal government employees in the course of their
official duties are not subject to copyright protection under 17 U.S.C.
105. COBOL programs written by agency staff are therefore in the public
domain and may be freely disclosed.

For code written by contractors, I request that the agency review the
applicable contract terms. Many federal contracts include Government
Purpose Rights or Unlimited Rights provisions (per DFARS 252.227-7014
or FAR 52.227-14) that permit government disclosure of deliverables.

### Format

I request that responsive records be provided in electronic format
(plain text files preferred). If the records exist on mainframe systems
in EBCDIC encoding, ASCII-converted copies are preferred but not
required.

### Response

I expect a response within 20 business days as required by 5 U.S.C.
552(a)(6)(A)(i). If you anticipate that processing this request will
require additional time, please contact me to discuss narrowing the
scope.

If any portion of this request is denied, please identify the specific
exemption(s) claimed for each withheld record and release all
reasonably segregable non-exempt portions.

Thank you for your attention to this request.

Sincerely,

[YOUR NAME]
[YOUR TITLE / AFFILIATION]
[YOUR EMAIL]
[YOUR PHONE]

---

## Submission Tips

1. **Submit to multiple agencies simultaneously.** Each agency has
   different COBOL systems and different FOIA cultures. Cast a wide
   net.

2. **SSA is the top target.** 60+ million lines of COBOL, the largest
   known federal COBOL estate. They process high FOIA volume so they
   have established procedures.

3. **Treasury/IRS will likely push back hardest** citing tax
   administration security. But decommissioned system code is a
   reasonable ask.

4. **OPM is actively modernizing** with TMF funds. They may be the
   most receptive since they're trying to move off COBOL right now.

5. **Follow up at 20 days.** Agencies routinely miss the statutory
   deadline. A polite follow-up citing the deadline keeps the request
   moving.

6. **Appeal any blanket denial.** If an agency denies the entire
   request citing security, appeal and argue that copybooks and
   decommissioned code are segregable and non-exempt.

7. **Consider also filing with state agencies** (unemployment insurance
   systems) under their respective open records laws. Same letter
   structure works with minor adjustments.
