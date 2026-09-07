# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# MASTER COMPLIANCE RULEBOOK: LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011
**Document Identifier:** LMD-CR-2026-V1.0  
**Effective Date:** September 6, 2026  
**Status:** Implementation-Ready Specification  

---

## 1. Statutory Framework and Governing Legislation
This rulebook defines the legal parameters and compliance verification logic for **SIH Problem Statement 2634** (Smart India Hackathon - Automated Legal Metrology Compliance Checker). Every automated check, software feature, and system action defined herein must be mapped directly to the following governing statutes:

1. **The Legal Metrology Act, 2009 (Act No. 1 of 2010):** The primary legislation providing the statutory mandate, powers of inspectors, seizure provisions, and core penalties [118].
2. **The Legal Metrology (Packaged Commodities) Rules, 2011 ("LMPC Rules"):** Enacted under Section 52 of the Act, defining the exact labeling standards, exemptions, and procedural requirements for "pre-packaged commodities" [118].
3. **Statutory Amendments (2011–2026):** Including the landmark 2017 e-commerce amendment [123], the 2021/2022 Unit Sale Price (USP) operationalization rules [123], the 2023 Combination Package exemptions [123], the 2025 Medical Devices carve-out [123], and the Jan Vishwas (Amendment of Provisions) Act, 2026 [123].

---

## 2. Mandatory Label and Listing Declarations (Rule 6)
Under **Rule 6(1)** and **Rule 6(10)** (the e-commerce display rule), every pre-packaged commodity sold in physical retail or offered on an e-commerce platform must bear the following seven mandatory declarations [1, 119]. E-commerce platforms must display these fields on the digital listing itself, with the sole exception of the month/year of packaging [121]:

### 2.1 Name and Address of Manufacturer, Packer, or Importer [Rule 6(1)(a)]
* **Legal Requirement:** The label and online listing must declare the name and complete postal address of the manufacturer [1, 121]. If the manufacturer is different from the packer, both names and addresses must appear [121]. For imported goods, the name and address of the Indian importer must be declared [121].
* **Postal Address Standard:** "Complete address" means the street name, city, state, and a valid 6-digit PIN code [121]. Terms such as "Marketed by [Firm]" are legally non-compliant unless accompanied by the explicit name and address of the manufacturer/packer/importer [121].
* **System Validation Logic:** Parse text to identify an entity name and a postal address containing a 6-digit regex match (`\b\d{6}\b`) and geographic terms. Flag missing/incomplete addresses [121].

### 2.2 Country of Origin [Rule 6(1)(a) Proviso / 2017 Amendment]
* **Legal Requirement:** Imported products must declare the country of origin, manufacture, or assembly [121]. Per Department of Consumer Affairs (DoCA) e-commerce guidelines, this field is mandatory on *all e-commerce listings* to allow consumers to filter and search products by origin [2, 121].
* **System Validation Logic:** The database must enforce a non-empty string mapped against valid ISO country names. Regex pattern: `^(Made in|Origin:|Country of Origin:)?\s*([A-Za-z\s]+)$` [121].

### 2.3 Common and Generic Product Name [Rule 6(1)(b)]
* **Legal Requirement:** The package and digital listing must declare the common or generic name of the commodity (e.g., "lodized Salt", "Laundry Detergent") [121]. Using only a brand or marketing name (e.g., "OxiBlast") without the generic name is a violation [121].
* **System Validation Logic:** Verify that a distinct generic name is present and is not identical to the brand name [150].

### 2.4 Net Quantity and Standard Units [Rule 6(1)(c) / Rules 11–13]
* **Legal Requirement:** Net weight, volume, or count must be declared using standard SI units [121]. Vague qualifiers like "approx.", "about", "when packed", or "family pack" are strictly illegal [121].
* **Standard Units:** Weight (mg, g, kg), Volume (ml, L), Length/Area (mm, cm, m, sq. m), or Count (N, Units, Pcs, Pair, Sets) [85, 121, 140].
* **System Validation Logic:** Verify format via regex: `^\d+(\.\d+)?\s*(mg|g|kg|ml|l|L|mm|cm|m|N|pcs|pcs\.|units|pair|sets)$` (case-insensitive). Reject non-standard units [80].

### 2.5 Month and Year of Manufacture [Rule 6(1)(d)]
* **Legal Requirement:** The package must bear the month and year of manufacture or pre-packing (or import for foreign goods) [121]. E-commerce listings are legally exempt from displaying the manufacturing date online, but the physical product image must show it if the Principal Display Panel (PDP) is depicted [96, 121].
* **System Validation Logic:** The date must parse to a valid MM/YYYY format and cannot be a future date relative to the inspection scan [121].

### 2.6 Maximum Retail Price (MRP) [Rule 6(1)(e)]
* **Legal Requirement:** The MRP must be printed on the package in Indian Rupees (₹), inclusive of all taxes, in the exact format "MRP Rs. ___ incl. of all taxes" or "MRP ₹ ___ (incl. of all taxes)" [121, 140]. E-commerce platforms must display this online, and the actual selling/transaction price must *never* exceed the declared MRP [3, 121].
* **System Validation Logic:** Double-pipeline check (OCR of package image and text parse of listing). The listed price must be $\le$ the printed MRP [4, 121].

### 2.7 Unit Sale Price (USP) [Rule 6(1)(e) Proviso / 2021 Amendment]
* **Legal Requirement:** For products sold by weight, measure, or count, the Unit Sale Price (price per standard g/kg, ml/L, cm/m, or number) must be declared near the MRP [121, 140]. 
* **Calculation Standard:** Rounded off to two decimal places [121].
  * If Net Qty is $<1$ kg / $1$ L / $1$ m: Declare price per g, ml, or cm [121].
  * If Net Qty is $\ge1$ kg / $1$ L / $1$ m: Declare price per kg, L, or m [121].
  * If sold by number: Declare price per single item (per number) [121].
* **System Validation Logic:** Cross-calculate: $\text{USP} \times \text{Net Quantity} \approx \text{MRP}$ (within $0.5\%$ rounding tolerance) [81, 121].

### 2.8 Consumer Care Details [Rule 6(2)]
* **Legal Requirement:** Every package and listing must clearly display the name, address, telephone number, and e-mail address of the person or office responsible for consumer complaints [121, 140].
* **System Validation Logic:** Check for presence of physical address, a valid 10-digit phone number, and a properly formatted email address [121].

---

## 3. Physical Compliance and Sticker Rules
The system must distinguish between physical package labeling compliance and e-commerce listing compliance. Visual features on product packaging must be checked for the following:

### 3.1 Prohibition of Individual Correction Stickers [Rule 6(3)–(6)]
* **Legal Mandate:** It is strictly illegal to affix individual correction stickers over mandatory declarations (MRP, Net Qty, Dates) to alter them [121, 140].
* **Sole Exception (Lower MRP):** A sticker is permitted *only* to reduce the MRP, provided the sticker does not completely obscure the original manufacturer's printed MRP [121, 140, 148].
* **Tax-Revision Exception (Rule 18(3)):** When taxes are revised by the government, a manufacturer may apply a sticker displaying the revised (higher) MRP, but only after publishing a public advertisement in newspapers and obtaining state-level permission [121, 132].
* **System Validation Logic:** Image-analysis pipeline flags any sticker detected over the MRP zone. If the sticker raises the price, it is flagged as a BLOCKER violation [121].

### 3.2 Principal Display Panel (PDP) and Font Specifications [Rule 7, 8, 9]
* **Principal Display Panel (PDP):** The largest flat surface of the packaging facing the consumer. All mandatory declarations must appear together on the PDP [121, 140].
* **Legibility & Contrast:** Numerals and letters must appear in a color that contrasts conspicuously with the background [121, 140].
* **Font Height Regulations:** Under **Rule 7 (Table I/II)**, the minimum height of numerals/letters on physical packaging depends on net quantity:
  * Net Quantity $\le 50\text{ g/ml}$: Min height $1.0\text{ mm}$ ($2.0\text{ mm}$ if blown/embossed) [121].
  * $50\text{ g/ml} < \text{Net Qty} \le 200\text{ g/ml}$: Min height $1.5\text{ mm}$ ($3.0\text{ mm}$ if blown/embossed).
  * $200\text{ g/ml} < \text{Net Qty} \le 1\text{ kg/L}$: Min height $2.0\text{ mm}$ ($4.0\text{ mm}$ if blown/embossed).
  * Net Quantity $> 1\text{ kg/L}$: Min height $4.0\text{ mm}$ ($6.0\text{ mm}$ if blown/embossed).
* **System Validation Logic:** If a physical calibration card is in-frame, calculate px/mm [66]. Measure character vertical height (excluding vertical padding) and cross-verify with Rule 7 limits [67].

---

## 4. Statutory Penalties and Liability Framework
All violations detected by the software must be categorized according to the **Legal Metrology Act, 2009** and **LMPC Rules, 2011**. Penalties are structured into distinct severity tiers, reflecting the **Jan Vishwas (Amendment of Provisions) Act, 2026** (effective May 1, 2026) which decriminalized specific administrative offenses but preserved criminal penalties for core pricing and labeling violations [122, 123, 132]:

### 4.1 Section 36(1) - Non-Conforming Packaging Declarations (Core Labeling Offense)
* **Scope:** Selling, manufacturing, packing, importing, or distributing any pre-packaged commodity that does not conform to the mandatory declarations (e.g., missing MRP, missing Origin, missing Consumer Care) [122]. This section applies to e-commerce platforms where they fail the "safe-harbor" test [122].
* **Jan Vishwas status:** **Not decriminalized** (as of current notifications) [122, 123].
* **Penalties:**
  * **First Offense:** Fine up to **₹25,000** [122].
  * **Second Offense:** Fine up to **₹50,000** [122].
  * **Subsequent Offenses:** Fine of **₹50,000 to ₹1,00,000**, or **imprisonment up to one year**, or both [122].
* **System Severity:** **BLOCKER** (if mandatory fields are missing) or **MAJOR** (if formatting is wrong) [78].

### 4.2 Section 18(2) - Selling Above MRP
* **Scope:** Retailers, online sellers, or distributors selling or offering a product at a transaction price exceeding the printed MRP on the package [121].
* **Penalties:** Aligned with Section 36(1) for packaging non-conformance (up to ₹25,000 for 1st offense, ₹50,000 for 2nd, and up to ₹1,00,000 or 1-year imprisonment for subsequent offenses) [9, 122].
* **System Severity:** **BLOCKER** [78].

### 4.3 Section 29 - Quoting or Publishing Non-Standard Units
* **Scope:** Using non-standard units (such as "lbs.", "inches" for non-textiles, or vague descriptors like "approx.") in commercial transactions or online descriptions [122].
* **Jan Vishwas Amendment (Post-May 1, 2026):** **Decriminalized** [122, 123].
  * **First Offense:** **Official Warning and an Improvement Notice** issued to the seller [122].
  * **Second Offense:** Penalty up to **₹50,000** [122].
  * **Subsequent Offenses:** Fine of **₹1,00,000 to ₹2,00,000** (imprisonment removed) [122].
* **System Severity:** **MAJOR** [78].

### 4.4 Section 31 - Non-Production of Documents
* **Scope:** Failure of a manufacturer, packer, importer, or seller to produce required compliance records (such as Rule 27 registrations or LMPC certificates) to a Legal Metrology Officer [122].
* **Jan Vishwas Amendment (Post-May 1, 2026):** **Decriminalized** [122, 123].
  * **First Offense:** **Official Warning and an Improvement Notice** [122].
  * **Second Offense:** Penalty up to **₹25,000** [122].
  * **Subsequent Offenses:** Fine of **₹50,000 to ₹1,00,000** (imprisonment removed) [122].
* **System Severity:** **MAJOR** [78].

---

## 5. Software Features vs. Legal Mandates
To maintain absolute legal integrity, the system must clearly demarcate automated software capabilities from statutory powers. AI output is legally an **advisory signal** to assist human inspectors, not an automated judicial ruling [91, 93]:

| Feature Area | Automated Software Capability (Proposed Feature) | Statutory/Legal Mandate (Human Officer Required) |
| :--- | :--- | :--- |
| **Violation Flagging** | Crawls listings, runs OCR/LLM checks, and flags potential MRP/Origin mismatches [100]. | Only a gazetted **Legal Metrology Officer (LMO)** can formally confirm a violation and issue a SCN [91, 103]. |
| **Evidence Collection** | Automatically captures hashed screenshots, generates BSA Section 63 stubs [100]. | Only the inspector can execute a physical search/seizure under Section 15 of the Act [104]. |
| **Penalty Calculation** | Queries registration history and suggests compounding fees or fine tiers [105]. | Only the state **Controller or Director of Legal Metrology** can pass compounding orders [104]. |
| **Seizure Trigger** | Detects severe, repeat pricing or counterfeit violations and alerts the regional circle [101]. | Physical search/seizure must strictly follow the BNSS/CrPC safeguards, requiring a manual "reason to believe" [93, 102]. |

---

## 6. Implementation Checklist for AI Developers
Developers implementing the rule engine must translate these rules into deterministic code. Use the following hierarchy for code logic:
1. **Filter Out-of-Scope Items First:** Check product weight, category, and seller type to apply correct exceptions before running compliance checks [43, 47].
2. **Never Auto-Average Discrepancies:** If two extraction pipelines (e.g., OCR vs. LLM) disagree, or if different panels show different MRPs, the system must force a `NEEDS_REVIEW` state [54, 84].
3. **Traceability:** Every validation failure must save the exact Rule/Section citation and the specific arithmetic or string comparison that triggered the fail [75].
