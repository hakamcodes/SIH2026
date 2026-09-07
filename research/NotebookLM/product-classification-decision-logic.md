# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# PRODUCT CLASSIFICATION & DECISION LOGIC SPECIFICATION
**Document Identifier:** LMD-PC-2026-V1.0  
**Effective Date:** September 6, 2026  
**Status:** Implementation-Ready Specification  

---

## 1. Introduction and Scope
To prevent erroneous violation reports, a Legal Metrology AI system must not treat all products identically [28]. It must first classify each product into its correct regulatory category, identify applicable exemptions, and apply category-specific rulesets [28, 43]. 

This specification defines the product categories, standard pack sizes, statutory exemptions, decision logic trees, and raw visual/metadata attributes that the machine-vision and rule-engine pipelines must detect before evaluating compliance [28, 44].

---

## 2. Product Category Rules and Standard Pack Sizes (Second Schedule)
Under **Rule 5** of the LMPC Rules, several high-volume consumer goods listed in the **Second Schedule** are subject to "standard packaging sizes" [30, 121]. Packaging in sizes outside this schedule is illegal unless specifically exempted (provisos allowing "non-standard pack size" declarations were withdrawn in 2012) [30, 43].

| Product Category | Prescribed Standard Pack Sizes (Second Schedule) | Specific Labeling Overlays |
| :--- | :--- | :--- |
| **Biscuits** | 25 g, 50 g, 75 g, 100 g, 150 g, 200 g, 250 g, 300 g, 350 g, 400 g, 450 g, 500 g, 600 g, 700 g, 800 g, 900 g, 1 kg [30]. | Standard LMPC retail declarations apply [30]. |
| **Non-Alcoholic Beverages** | Mineral water, drinking water, soft drinks: 100 ml, 200 ml, 250 ml, 300 ml, 330 ml (cans), 500 ml, 750 ml, 1 L, 1.5 L, 2 L, 3 L, 4 L, 5 L [30]. | Mineral/drinking water bottle volumes are strictly enforced [30]. |
| **Edible Oils, Ghee, Vanaspati** | 50 g, 100 g, 200 g, 500 g, 1 kg, 2 kg, 3 kg, 5 kg (and equivalent volume in ml/L at $30^\circ\text{C}$) [30]. | Must declare net weight or net volume [30]. |
| **Soaps & Detergents** | **Toilet Soap:** 25 g, 50 g, 75 g, 100 g, 125 g, 150 g, or multiples of 50 g [30].  <br>**Laundry Soap:** 50 g, 75 g, 100 g, or multiples of 50 g [30].  <br>**Detergent Powder:** 50 g, 100 g, 200 g, 500 g, 1 kg, 2 kg, or multiples of 1 kg [30]. | Soaps/detergents may add "when packed" next to net quantity [121]. |
| **Bread** | Un-sliced and sliced bread (excluding specialty buns): Multiples of 100 g (e.g., 100 g, 200 g, 400 g, 800 g) [30]. | Exempt from date of manufacture if "best before" is clearly visible [96]. |
| **Milk Powder** | Below 50 g: Unrestricted [30].  <br>Above 50 g: 50 g, 100 g, 200 g, 500 g, 1 kg, 2 kg, 5 kg [30]. | Must use "g" or "kg" units [30]. |
| **Cement (Bagged)** | 1 kg to 25 kg (any size), 40 kg (for white cement), and 50 kg [30]. | Exempt from Chapter II declarations if sold direct to institutional buyers [32]. |

---

## 3. Statutory Exceptions and Exemption Rules (Rule 26)
Certain product categories, pack weights, or end-use cases alter or waive the standard labeling obligations under **Rule 26** and other LMPC provisos [33]:

### 3.1 Net Quantity $\le 10$ g or $\le 10$ ml [Rule 26(a)]
* **LMPC Effect:** **Fully Exempt.** Packages with a net quantity of 10 g / 10 ml or less (excluding tobacco/cigarettes) require no LMPC labeling (no printed MRP, dates, or manufacturer details) [30, 32].
* **The 10–20 g/ml Proviso:** Packages containing between 10 g (or 10 ml) and 20 g (or 20 ml) are *partially exempt*; they **must** still declare the MRP and Net Quantity, but are exempt from other Rule 6 declarations [30, 32].
* **System Logic:** If $\text{Net Qty} \le 10\text{ g/ml}$, bypass all checks. If $10\text{ g/ml} < \text{Net Qty} \le 20\text{ g/ml}$, evaluate ONLY MRP and Net Quantity [30, 32].

### 3.2 Takeaway Hotel or Restaurant Food [Rule 26(b)]
* **LMPC Effect:** **Fully Exempt.** Any ready-to-eat food packed by a hotel, restaurant, or take-away counter is exempt from LMPC packaging declarations [30, 32].
* **System Logic:** If `commodity.category == restaurant_food`, bypass all LMPC rules [121].

### 3.3 DPCO Price-Controlled Drugs [Rule 26(c)]
* **LMPC Effect:** **Fully Exempt.** Formulations listed under the Drug (Price Control) Order (DPCO) are exempt from LMPC labeling because their prices are regulated directly by the National Pharmaceutical Pricing Authority (NPPA) under the Drugs Act [30, 32].
* **System Logic:** If `commodity.category == dpco_drug`, flag as out of scope. Note: Medical devices are NOT covered under this drug exemption [121].

### 3.4 Bulky Agricultural Produce $> 50$ kg [Rule 26(d)]
* **LMPC Effect:** **Fully Exempt.** Bulky agricultural produce (such as bags of grain, rice, or pulses) in packages exceeding 50 kg is exempt from Chapter II labeling [32].
* **System Logic:** If `commodity.category == agricultural_produce` AND `net_quantity > 50 kg`, bypass checks [121].

### 3.5 Loose (Non-Prepackaged) Garments or Hosiery
* **LMPC Effect:** **Out of Packaged Scope.** Loose garments sold off hangers or without sealed packaging are not pre-packaged commodities [30, 32].
* **Required Tagging Alternative:** Although exempt from full LMPC packaging rules, retailers must still display a tag with: Product Name/Description, size (metric dimensions in cm + S/M/L tag), MRP, and manufacturer/importer address [30, 32].
* **System Logic:** If `packaging_status == loose` AND `commodity.category == apparel`, bypass standard Rule 6 checks and apply the *Garment Tag rules* instead [30, 32].

### 3.6 Specialty/Industrial Packages (Rule 3)
* **LMPC Effect:** **Out of Chapter II Scope.** Bulk packs intended solely for industrial use (for processing in a factory) or institutional use (sold direct to hotels, airlines, hospitals) are exempt from retail labeling rules [30, 32]. These packages must bear the marking "Not for Retail Sale" [45].
* **System Logic:** If `packaging_type == industrial_or_institutional`, evaluate ONLY Rule 24 declarations (manufacturer, commodity name, and total count/weight) [121].

### 3.7 Medical Devices Carve-Out (2025 Amendment - GSR 778(E))
* **LMPC Effect:** **Partial Carve-Out.** PDP font size, height, and placement for registered medical devices are governed strictly by the Medical Devices Rules, 2017 [98, 121]. The LMPC Rules do not apply to PDP layout checks for this category, although MRP, USP, and Consumer Care details are still required [98].
* **System Logic:** If `commodity.category == medical_device`, bypass LMPC font-size (Rule 7) and PDP placement (Rule 8) checks. Validate only MRP, USP, and Consumer Care [98].

---

## 4. Logical Decision Trees for Compliance Routing
The following 10 decision paths represent the logical steps the software must execute to determine which rules apply to a given product [33]:

```
                                  [Input SKU Data/Images]
                                             │
                                             ▼
                                  Is it Pre-Packaged? [44]
                                    /                 \
                                  YES                  NO (Loose Good)
                                  /                      \
                    Net Qty <= 10g/ml? [47]            Is it Apparel?
                       /          \                      /         \
                     YES          NO                   YES          NO
                     /              \                  /              \
         [Statutory Exempt]    Determine Category    Apply Tag   [Exempt from LMPC]
                                 & Subtype [44]      Rules [38]
```

### Path 1: Biscuits (200 g Retail Pack)
1. **Packaging Status:** Sealed, pre-packaged [34].
2. **Category:** Consumable Food $\rightarrow$ listed in Second Schedule [34].
3. **Pack Type:** Retail, sold to ultimate consumer [34].
4. **Exemption Check:** Net quantity is 200 g ($>10\text{ g}$) $\rightarrow$ no Rule 26 exemption applies [34].
5. **Standard Size Check:** 200 g is a permitted size in the Second Schedule $\rightarrow$ **PASS** [34, 41].
6. **Apply Ruleset:** Apply full LMPC declarations (Manufacturer, Country of Origin, Generic Name, Net Qty, Mfg Date, MRP, USP, Consumer Care) [34, 121].

### Path 2: Imported Mineral Water (500 ml Bottle)
1. **Packaging Status:** Sealed, pre-packaged [35].
2. **Category:** Non-Alcoholic Beverage $\rightarrow$ listed in Second Schedule [30, 35].
3. **Pack Type:** Retail [35].
4. **Exemption Check:** Net quantity is 500 ml ($>10\text{ ml}$) $\rightarrow$ no Rule 26 exemption [35].
5. **Standard Size Check:** 500 ml is a standard volume size $\rightarrow$ **PASS** [30].
6. **Origin Check:** Mapped as `is_imported == true` $\rightarrow$ **Trigger Rule 6(1)(a) Proviso** [35, 121].
7. **Apply Ruleset:** Apply all retail declarations plus mandatory **Country of Origin** and **Importer Name/Address** [35, 121].

### Path 3: Laundry Detergent (Wholesale Box of 12 Packs)
1. **Packaging Status:** Sealed carton containing multiple units [36].
2. **Category:** Non-Soapy Detergent Powder [36].
3. **Pack Type:** Wholesale (not sold directly to ultimate consumer as a single unit) [36].
4. **Exemption Check:** Total weight $>10\text{ g}$ $\rightarrow$ no Rule 26 exemption [36].
5. **Apply Ruleset:** **Bypass Rule 6.** Apply **Rule 24 (Wholesale Rules)**: Verify only Manufacturer Details, Commodity Name, and Total Quantity (e.g., "12 Retail Packs") [36, 121].

### Path 4: Packaged Silk Saree (1 Piece)
1. **Packaging Status:** Pre-packaged in a sealed cardboard/plastic retail box [37].
2. **Category:** Textile / Apparel [37].
3. **Pack Type:** Retail [37].
4. **Exemption Check:** None [37].
5. **Apply Ruleset:** Apply standard declarations [37]. **Trigger Rule 6(1)(f) (Dimensions Rule)**: Verify presence of finished size dimensions (length $\times$ width in meters, e.g., "5.5 m $\times$ 1.1 m") [37, 121].

### Path 5: Men's Cotton Shirt (Sold Loose in Retail Store)
1. **Packaging Status:** Loose, unpackaged [38].
2. **Category:** Textile / Apparel [38].
3. **Pack Type:** Retail [38].
4. **Exemption Check:** Mapped as `pre_packaged == false` $\rightarrow$ **Statutory Exemption from LMPC Rules** [38].
5. **Apply Ruleset:** Bypass all LMPC declarations [38]. Verify alternative garment tagging display (Brand, Size in cm, MRP, Manufacturer Address) [38].

### Path 6: Craft Beer (330 ml Bottle Combo Pack)
1. **Packaging Status:** Sealed glass bottle [39].
2. **Category:** Alcoholic Beverage [39].
3. **Pack Type:** Retail [39].
4. **Exemption Check:** Governed primarily by State Excise Laws [39].
5. **Apply Ruleset:** Excise laws override LMPC pricing and date rules [39]. Bypass LMPC manufacturing date and MRP format checks, but enforce Net Quantity (330 ml is standard) and Manufacturer Name [39, 121].

### Path 7: Imported Perfume (100 ml Glass Bottle)
1. **Packaging Status:** Sealed glass bottle in retail carton [40].
2. **Category:** Cosmetics [40].
3. **Pack Type:** Retail [40].
4. **Origin Check:** Mapped as `is_imported == true` [40].
5. **Exemption Check:** Manufacturing date and expiry are governed strictly by the Drugs & Cosmetics Rules [40].
6. **Apply Ruleset:** Bypass LMPC date checks [40, 121]. Verify Country of Origin, Importer Details, MRP, Net Quantity (100 ml), and Consumer Care [40, 121].

### Path 8: Basmati Rice (5 kg Retail Polybag)
1. **Packaging Status:** Sealed plastic polybag [41].
2. **Category:** Consumable Grain (Food) [30, 41].
3. **Pack Type:** Retail [41].
4. **Exemption Check:** None [41].
5. **Standard Size Check:** 5 kg is a standard pack size [30, 41].
6. **Apply Ruleset:** Apply full LMPC retail declarations. Date check: Defer manufacturing/batch details to FSSAI rules, but keep LMPC pricing and Net Quantity [30, 121].

### Path 9: Mint Candy (8 g Pouch)
1. **Packaging Status:** Sealed foil pouch [41].
2. **Category:** Consumable Food [41].
3. **Pack Type:** Retail [41].
4. **Exemption Check:** Net weight is 8 g ($\le10\text{ g}$) $\rightarrow$ **Triggers Rule 26(a) Exemption** [41].
5. **Apply Ruleset:** **Exempt from all LMPC labeling rules.** Do not flag for missing MRP, dates, or manufacturer details [41, 42].

### Path 10: Coconut Oil (20 L Commercial Drum)
1. **Packaging Status:** Sealed industrial-grade plastic drum [42].
2. **Category:** Edible Oil [42].
3. **Pack Type:** Wholesale / Commercial (not intended for retail consumer) [42].
4. **Standard Size Check:** Edible oil retail standard sizes top out at 5 kg/L [30, 42]. 20 L is commercial size [42].
5. **Apply Ruleset:** Enforce **Rule 24 (Wholesale)**: Verify Manufacturer Details, Commodity Name, and Total Volume (20 L) [42, 121].

---

## 5. Machine-Vision Input Parameters (The Detection Payload)
To execute the decision paths above, the computer vision pipeline must extract and structure the following 12 attributes from the raw product images and e-commerce listing text [44]:

```json
{
  "image_analysis_parameters": {
    "packaging_status": "pre_packaged | loose",
    "product_category": "food | beverage | chemical | textile | cosmetic | pharmaceutical | medical_device | hardware",
    "commodity_subtype": "biscuits | water | detergent | soap | paint | garment | medicine | bulk_grain | other",
    "packaging_type": "retail | wholesale | industrial",
    "net_quantity": {
      "declared_value": 250.00,
      "declared_unit": "g | kg | ml | l | cm | m | N | pcs | pair | sets"
    },
    "is_imported": true,
    "manufacturer_info_present": true,
    "mrp_price": {
      "value": 150.00,
      "currency": "INR",
      "format_compliant": true
    },
    "packing_date": {
      "month": 1,
      "year": 2026,
      "raw_text_detected": "MFD 01/2026"
    },
    "special_declarations": {
      "best_before_present": true,
      "country_of_origin": "Vietnam",
      "dimensions_declared": null
    },
    "exemption_flags": {
      "under_10g_ml": false,
      "hotel_ready_to_eat": false,
      "dpco_drug": false,
      "bulk_agri_over_50kg": false
    },
    "other_regulator_mapping": "FSSAI | Drugs_Act | Medical_Devices_Rules | None"
  }
}
```

The machine-vision pipeline must populates this schema. If any field is ambiguous or unreadable, it must default to `null` to force the rule engine to routing to the `NEEDS_REVIEW` triage queue [54, 84].
