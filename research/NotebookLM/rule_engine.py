import json
import re
from datetime import datetime

class ComplianceEngine:
    def __init__(self, rules_path=None):
        self.rules = []
        if rules_path:
            with open(rules_path, 'r') as f:
                self.rules = json.load(f)
        else:
            # Fallback to standard path
            try:
                with open('/workspace/artifacts/machine-readable-compliance-rules.json', 'r') as f:
                    self.rules = json.load(f)
            except Exception:
                pass

        self.valid_countries = [
            "India", "Vietnam", "China", "USA", "Japan", "Germany", 
            "Bangladesh", "Thailand", "Malaysia", "Sri Lanka", "Indonesia"
        ]

    def to_base_unit(self, value, unit):
        if value is None or unit is None:
            return None
        unit = unit.lower().strip()
        if unit == 'g':
            return value
        elif unit == 'kg':
            return value * 1000.0
        elif unit == 'mg':
            return value / 1000.0
        elif unit == 'ml':
            return value
        elif unit in ['l', 'L']:
            return value * 1000.0
        elif unit == 'cm':
            return value
        elif unit == 'm':
            return value * 100.0
        elif unit == 'mm':
            return value / 10.0
        elif unit in ['n', 'pcs', 'units', 'pair', 'sets', 'pcs.']:
            return value
        return value

    def round_mrp_paise(self, x):
        if x is None:
            return None
        rupees = int(x)
        paise = round((x - rupees) * 100)
        if paise < 50:
            return float(rupees)
        elif 50 <= paise <= 95:
            return float(rupees) + 0.50
        else:
            return float(rupees + 1)

    def is_close(self, val1, val2):
        if val1 is None or val2 is None:
            return False
        return abs(val1 - val2) <= max(0.01, 0.005 * val2)

    def check_rule_applicability(self, rule_id, product, scan_date=None):
        commodity = product.get('commodity', {})
        is_exempt = commodity.get('is_exempt', False)
        category = commodity.get('category', '')
        subtype = commodity.get('subtype', '')
        is_imported = commodity.get('is_imported', False)
        scan_source = product.get('scan_source', 'package_image')
        
        if is_exempt and rule_id not in ['LM-T01', 'LM-U01', 'LM-U02']:
            # Exempt commodities are exempt from normal packaging rules
            net_qty = product.get('net_quantity', {})
            val = net_qty.get('value')
            unit = net_qty.get('unit')
            if val is not None and unit in ['g', 'ml']:
                if 10.0 < val <= 20.0:
                    if rule_id in ['LM-C01', 'LM-C02', 'LM-F01', 'LM-F02', 'LM-F03']:
                        return True
            return False

        if rule_id == 'LM-C01':
            return True
        elif rule_id == 'LM-C02':
            return category != 'alcoholic_beverage'
        elif rule_id == 'LM-C03':
            return True
        elif rule_id == 'LM-C04':
            return is_imported == True
        elif rule_id == 'LM-C05':
            return scan_source == 'package_image' and category not in ['bidi', 'incense_sticks', 'lpg_cylinder']
        elif rule_id == 'LM-C06':
            return True
        elif rule_id == 'LM-C07':
            return True
        elif rule_id == 'LM-C08':
            return category in ['food', 'beverage', 'perishable']
        elif rule_id == 'LM-C09':
            return category == 'textile'
            
        elif rule_id == 'LM-F01':
            return product.get('net_quantity', {}).get('unit') is not None
        elif rule_id == 'LM-F02':
            return product.get('net_quantity', {}).get('value') is not None
        elif rule_id == 'LM-F03':
            return product.get('mrp', {}).get('value') is not None
        elif rule_id == 'LM-F04':
            return scan_source == 'package_image' and product.get('mrp', {}).get('raw_text') is not None
        elif rule_id == 'LM-F05':
            return product.get('mfg_date') is not None
        elif rule_id == 'LM-F06':
            return product.get('country_of_origin') is not None
        elif rule_id == 'LM-F07':
            return product.get('consumer_care') is not None or 'consumer_care' in product
            
        elif rule_id == 'LM-M01':
            is_combo = subtype in ['combination_package', 'group_package', 'multi_piece_package'] or category in ['combination_package', 'group_package', 'multi_piece_package']
            return product.get('usp_declared') is not None and not is_combo
        elif rule_id == 'LM-M02':
            return 'panel_a' in product and 'panel_b' in product
        elif rule_id == 'LM-M03':
            return product.get('mrp', {}).get('computed_value') is not None
        elif rule_id == 'LM-M04':
            is_scheduled = subtype in ['biscuits', 'drinking_water', 'mineral_water', 'baby_food', 'detergent_powder', 'toilet_soap', 'laundry_soap', 'bread', 'milk_powder', 'cement']
            return is_scheduled
            
        elif rule_id == 'LM-X01':
            return 'mrp_candidates' in product and len(product.get('mrp_candidates', [])) > 0
        elif rule_id == 'LM-X02':
            return product.get('sticker_detected') == True
        elif rule_id == 'LM-X03':
            return 'listing_data' in product and 'package_ocr_data' in product
        elif rule_id == 'LM-X04':
            return product.get('listing_data', {}).get('price') is not None and product.get('mrp', {}).get('value') is not None
            
        elif rule_id == 'LM-T01':
            return True
        elif rule_id == 'LM-T02':
            mfg = product.get('mfg_date')
            expiry = product.get('best_before_date') or product.get('expiry_date') or product.get('use_by_date')
            return mfg is not None and expiry is not None
            
        elif rule_id == 'LM-U01':
            confidences = product.get('field_confidences', {})
            return 'field_confidences' in product or len(confidences) > 0
        elif rule_id == 'LM-U02':
            return 'ocr_pipeline' in product and 'llm_pipeline' in product
            
        return False

    def evaluate_rule(self, rule_id, product, scan_date="2026-09-06"):
        rule_meta = next((r for r in self.rules if r['rule_id'] == rule_id), None)
        severity = rule_meta.get('severity', 'BLOCKER') if rule_meta else 'BLOCKER'
        on_fail_code = rule_meta.get('on_fail_code', 'MISSING_DECLARATION') if rule_meta else 'MISSING_DECLARATION'
        
        if not self.check_rule_applicability(rule_id, product, scan_date):
            return "NOT_APPLICABLE", None, "Rule is not applicable to this product."

        if rule_id == 'LM-C01':
            net_qty = product.get('net_quantity', {})
            val = net_qty.get('value')
            unit = net_qty.get('unit')
            if val is not None and unit is not None:
                return "PASS", None, "Net Quantity is declared."
            return "FAIL", "MISSING_DECLARATION", "Net Quantity is missing or not declared."

        elif rule_id == 'LM-C02':
            mrp = product.get('mrp', {})
            val = mrp.get('value')
            if val is not None:
                return "PASS", None, "Maximum Retail Price (MRP) is declared."
            return "FAIL", "MISSING_DECLARATION", "Maximum Retail Price (MRP) is missing or not declared."

        elif rule_id == 'LM-C03':
            mfg_info = product.get('manufacturer_or_packer_or_importer', {})
            name = mfg_info.get('name')
            address = mfg_info.get('address')
            if name and address:
                return "PASS", None, "Manufacturer/Packer/Importer details are declared."
            return "FAIL", "MISSING_DECLARATION", "Manufacturer/Packer/Importer details are missing."

        elif rule_id == 'LM-C04':
            coo = product.get('country_of_origin')
            if coo and coo.strip() != "":
                return "PASS", None, "Country of Origin is declared."
            return "FAIL", "MISSING_DECLARATION", "Country of Origin is missing for imported product."

        elif rule_id == 'LM-C05':
            mfg_date = product.get('mfg_date') or product.get('mfg_or_pack_or_import_month_year')
            if mfg_date:
                return "PASS", None, f"Month and year of manufacture declared: {mfg_date}."
            return "FAIL", "MISSING_DECLARATION", "Month and year of manufacture is missing."

        elif rule_id == 'LM-C06':
            cc = product.get('consumer_care', {})
            phone = cc.get('phone') if isinstance(cc, dict) else None
            email = cc.get('email') if isinstance(cc, dict) else None
            if phone or email:
                return "PASS", None, "Consumer care contact details are declared."
            return "FAIL", "MISSING_DECLARATION", "Consumer care contact details (phone and/or email) are missing."

        elif rule_id == 'LM-C07':
            common_name = product.get('common_or_generic_name')
            brand_name = product.get('brand_name')
            if common_name and common_name.strip() != "":
                if common_name != brand_name:
                    return "PASS", None, f"Common product name is declared: {common_name}."
                return "FAIL", "MISSING_DECLARATION", "Common/generic name cannot be identical to the brand name."
            return "FAIL", "MISSING_DECLARATION", "Common/generic product name is missing."

        elif rule_id == 'LM-C08':
            bb = product.get('best_before_date') or product.get('use_by_date')
            if bb:
                return "PASS", None, f"Best Before / Use By date is declared: {bb}."
            return "FAIL", "MISSING_DECLARATION", "Best Before or Use By date is missing for perishable commodity."

        elif rule_id == 'LM-C09':
            dims = product.get('dimensions', {})
            length = dims.get('length')
            width = dims.get('width')
            if length and width:
                return "PASS", None, f"Textile dimensions declared: {length} x {width}."
            return "FAIL", "MISSING_DECLARATION", "Finished dimensions are missing for packaged textiles."

        elif rule_id == 'LM-F01':
            net_qty = product.get('net_quantity', {})
            unit = net_qty.get('unit')
            if unit in ['g', 'kg', 'mg', 'ml', 'l', 'L', 'cm', 'm', 'mm', 'N', 'pcs', 'units', 'pair', 'sets', 'pcs.']:
                return "PASS", None, f"Net quantity unit is standard: {unit}."
            return "FAIL", "INVALID_FORMAT", f"Net quantity unit '{unit}' is not standard SI unit."

        elif rule_id == 'LM-F02':
            net_qty = product.get('net_quantity', {})
            val = net_qty.get('value')
            try:
                val_float = float(val)
                if val_float > 0:
                    return "PASS", None, f"Net quantity value is positive and numeric: {val}."
                return "FAIL", "INVALID_FORMAT", f"Net quantity value '{val}' must be positive."
            except (ValueError, TypeError):
                return "FAIL", "INVALID_FORMAT", f"Net quantity value '{val}' is not numeric."

        elif rule_id == 'LM-F03':
            mrp = product.get('mrp', {})
            val = mrp.get('value')
            marker = mrp.get('currency_marker')
            try:
                val_float = float(val)
                if val_float <= 0:
                    return "FAIL", "INVALID_FORMAT", f"MRP value '{val}' must be positive."
                if marker in ['₹', 'Rs.', 'Rs']:
                    return "PASS", None, f"MRP is valid: {marker} {val}."
                return "FAIL", "INVALID_FORMAT", f"MRP currency marker '{marker}' is invalid."
            except (ValueError, TypeError):
                return "FAIL", "INVALID_FORMAT", f"MRP value '{val}' is not numeric."

        elif rule_id == 'LM-F04':
            mrp = product.get('mrp', {})
            raw_text = mrp.get('raw_text', '')
            if raw_text:
                if 'inclusive of all taxes' in raw_text.lower() or 'incl.' in raw_text.lower() or 'incl' in raw_text.lower():
                    return "PASS", None, "MRP contains the mandatory taxes suffix."
                return "FAIL", "INVALID_FORMAT", f"MRP raw text '{raw_text}' is missing 'inclusive of all taxes' suffix."
            return "PASS", None, "MRP raw text not captured, skipping suffix check."

        elif rule_id == 'LM-F05':
            mfg = product.get('mfg_date')
            try:
                mfg_parsed = datetime.strptime(mfg, "%Y-%m-%d")
                scan_parsed = datetime.strptime(scan_date, "%Y-%m-%d")
                if mfg_parsed <= scan_parsed:
                    return "PASS", None, f"Mfg date is valid and in past: {mfg}."
                return "FAIL", "INVALID_FORMAT", f"Mfg date '{mfg}' cannot be in the future relative to scan date '{scan_date}'."
            except Exception:
                return "FAIL", "INVALID_FORMAT", f"Mfg date '{mfg}' has invalid calendar format (expected YYYY-MM-DD)."

        elif rule_id == 'LM-F06':
            coo = product.get('country_of_origin')
            if coo in self.valid_countries:
                return "PASS", None, f"Country of Origin '{coo}' is recognized."
            return "FAIL", "INVALID_FORMAT", f"Country of Origin '{coo}' is unrecognized or invalid."

        elif rule_id == 'LM-F07':
            cc = product.get('consumer_care', {})
            phone = cc.get('phone') if isinstance(cc, dict) else None
            email = cc.get('email') if isinstance(cc, dict) else None
            phone_ok = False
            email_ok = False
            
            if phone:
                clean_phone = re.sub(r'[-\s]', '', phone)
                if re.match(r'^\+?91?\d{10}$', clean_phone) or re.match(r'^\d{10}$', clean_phone):
                    phone_ok = True
                    
            if email:
                if re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email):
                    email_ok = True
                    
            if phone_ok or email_ok:
                return "PASS", None, f"Consumer care contact is validly formatted (phone: {phone_ok}, email: {email_ok})."
            return "FAIL", "INVALID_FORMAT", f"Consumer care contact details are poorly formatted (phone: {phone}, email: {email})."

        elif rule_id == 'LM-M01':
            net_qty = product.get('net_quantity', {})
            val = net_qty.get('value')
            unit = net_qty.get('unit')
            mrp = product.get('mrp', {})
            mrp_val = mrp.get('value')
            usp_declared = product.get('usp_declared')
            
            base_val = self.to_base_unit(val, unit)
            if base_val is not None and mrp_val is not None:
                computed_usp = mrp_val / base_val
                if self.is_close(usp_declared, computed_usp):
                    return "PASS", None, f"Declared USP ₹{usp_declared} matches calculated USP ₹{computed_usp:.4f}."
                return "FAIL", "MATH_MISMATCH", f"Declared USP ₹{usp_declared} does not match calculated USP ₹{computed_usp:.4f}."
            return "FAIL", "MATH_MISMATCH", "Cannot calculate USP due to missing Qty or MRP."

        elif rule_id == 'LM-M02':
            panel_a = product.get('panel_a', {}).get('net_quantity', {})
            panel_b = product.get('panel_b', {}).get('net_quantity', {})
            val_a = panel_a.get('value')
            unit_a = panel_a.get('unit')
            val_b = panel_b.get('value')
            unit_b = panel_b.get('unit')
            
            base_a = self.to_base_unit(val_a, unit_a)
            base_b = self.to_base_unit(val_b, unit_b)
            if base_a is not None and base_b is not None:
                diff = abs(base_a - base_b)
                allowed_diff = 0.01 * base_a
                if diff <= allowed_diff:
                    return "PASS", None, f"Panel A ({base_a}g) matches Panel B ({base_b}g) within 1% tolerance."
                return "FAIL", "MATH_MISMATCH", f"Front panel quantity ({val_a} {unit_a}) does not match back panel ({val_b} {unit_b})."
            return "FAIL", "MATH_MISMATCH", "Cannot check cross-panel weight mismatch due to missing panel quantities."

        elif rule_id == 'LM-M03':
            mrp = product.get('mrp', {})
            actual_val = mrp.get('value')
            computed_val = mrp.get('computed_value')
            expected_val = self.round_mrp_paise(computed_val)
            if actual_val == expected_val:
                return "PASS", None, f"MRP ₹{actual_val} complies with statutory rounding of computed ₹{computed_val}."
            return "FAIL", "MATH_MISMATCH", f"MRP ₹{actual_val} is wrongly rounded. Computed ₹{computed_val} should round to ₹{expected_val}."

        elif rule_id == 'LM-M04':
            net_qty = product.get('net_quantity', {})
            val = net_qty.get('value')
            unit = net_qty.get('unit')
            subtype = product.get('commodity', {}).get('subtype', '')
            
            standard_sizes = []
            if subtype == 'biscuits':
                standard_sizes = [25, 50, 75, 100, 150, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000]
                
            if unit == 'g' and val in standard_sizes:
                return "PASS", None, f"Scheduled biscuit pack size '{val} g' is a standard size."
            
            if product.get('usp_declared') is not None:
                return "PASS", None, f"Non-standard pack size '{val} {unit}' for scheduled '{subtype}' but USP is declared."
            return "FAIL", "MISSING_DECLARATION", f"Scheduled '{subtype}' uses non-standard size '{val} {unit}' but does not declare USP."

        elif rule_id == 'LM-X01':
            candidates = product.get('mrp_candidates', [])
            distinct_mrp = set(candidates)
            if len(distinct_mrp) == 1:
                return "PASS", None, "Only a single printed MRP exists."
            return "FAIL", "CONFLICTING_DECLARATION", f"Multiple printed MRPs found: {candidates}. Dual pricing is illegal."

        elif rule_id == 'LM-X02':
            original_mrp = product.get('original_mrp', {})
            orig_visible = original_mrp.get('is_visible', False)
            orig_val = original_mrp.get('value')
            
            sticker = product.get('sticker', {})
            revised_val = sticker.get('mrp_value')
            reason = sticker.get('reason')
            
            if orig_visible and revised_val is not None and orig_val is not None:
                if revised_val < orig_val:
                    if reason:
                        return "PASS", None, f"Valid sticker MRP revision from ₹{orig_val} down to ₹{revised_val} (Reason: '{reason}')."
                    return "FAIL", "INVALID_REVISION", "Stickered MRP revision is missing a documented reason."
                return "FAIL", "INVALID_REVISION", f"Sticker revised price ₹{revised_val} must be lower than original MRP ₹{orig_val}."
            if not orig_visible:
                return "FAIL", "INVALID_REVISION", "Original printed MRP must remain visible when a sticker is applied."
            return "FAIL", "INVALID_REVISION", "Missing sticker or original MRP data."

        elif rule_id == 'LM-X03':
            listing = product.get('listing_data', {})
            package = product.get('package_ocr_data', {})
            
            mismatch_fields = []
            for field in ['net_quantity', 'country_of_origin', 'manufacturer_name']:
                list_v = listing.get(field)
                pack_v = package.get(field)
                if list_v != pack_v:
                    mismatch_fields.append(f"{field} ('{list_v}' vs '{pack_v}')")
            if not mismatch_fields:
                return "PASS", None, "Online listing details strictly match the physical product label."
            return "FAIL", "CONFLICTING_DECLARATION", f"Mismatch between online listing and physical label: {', '.join(mismatch_fields)}."

        elif rule_id == 'LM-X04':
            list_price = product.get('listing_data', {}).get('price')
            mrp_val = product.get('mrp', {}).get('value')
            if list_price is not None and mrp_val is not None:
                if list_price <= mrp_val:
                    return "PASS", None, f"Online selling price ₹{list_price} is <= printed MRP ₹{mrp_val}."
                return "FAIL", "OVERCHARGING_MRP", f"Online selling price ₹{list_price} exceeds printed MRP ₹{mrp_val}."
            return "FAIL", "OVERCHARGING_MRP", "Cannot verify online transaction price due to missing data."

        elif rule_id == 'LM-T01':
            try:
                scan_dt = datetime.strptime(scan_date, "%Y-%m-%d")
                base_dt = datetime.strptime("2011-04-01", "%Y-%m-%d")
                if scan_dt >= base_dt:
                    return "PASS", None, f"Ruleset version is legally effective on scan date: {scan_date}."
                return "FAIL", "STALE_RULESET", f"Scan date '{scan_date}' is prior to LMPC 2011 effective date."
            except Exception:
                return "FAIL", "STALE_RULESET", "Invalid scan date format."

        elif rule_id == 'LM-T02':
            mfg = product.get('mfg_date')
            expiry = product.get('best_before_date') or product.get('expiry_date') or product.get('use_by_date')
            try:
                mfg_parsed = datetime.strptime(mfg, "%Y-%m-%d")
                exp_parsed = datetime.strptime(expiry, "%Y-%m-%d")
                if mfg_parsed <= exp_parsed:
                    return "PASS", None, f"Mfg date ({mfg}) is before expiry ({expiry})."
                return "FAIL", "INVALID_FORMAT", f"Mfg date '{mfg}' cannot be after best before / expiry date '{expiry}'."
            except Exception:
                return "FAIL", "INVALID_FORMAT", "Invalid date format for comparison."

        elif rule_id == 'LM-U01':
            confidences = product.get('field_confidences', {})
            net_qty_conf = confidences.get('net_quantity', 1.0)
            mrp_conf = confidences.get('mrp', 1.0)
            
            low_fields = []
            if net_qty_conf < 0.75:
                low_fields.append(f"net_quantity ({net_qty_conf:.2f})")
            if mrp_conf < 0.80:
                low_fields.append(f"mrp ({mrp_conf:.2f})")
                
            if not low_fields:
                return "PASS", None, "All blocker fields meet minimum confidence thresholds."
            return "REVIEW", "NEEDS_REVIEW", f"Low field confidence on blocker fields: {', '.join(low_fields)}. Manual review is required."

        elif rule_id == 'LM-U02':
            ocr_p = product.get('ocr_pipeline', {})
            llm_p = product.get('llm_pipeline', {})
            ocr_num = ocr_p.get('numeric_val')
            llm_num = llm_p.get('numeric_val')
            
            if ocr_num is not None and llm_num is not None:
                diff = abs(ocr_num - llm_num)
                allowed_diff = 0.001 * ocr_num
                if diff <= allowed_diff:
                    return "PASS", None, f"Pipelines agree on numeric value (OCR: {ocr_num}, LLM: {llm_num})."
                return "REVIEW", "NEEDS_REVIEW", f"Dual-pipeline disagreement on numeric value: OCR={ocr_num}, LLM={llm_num}. Manual review is required."
            return "REVIEW", "NEEDS_REVIEW", "Missing pipeline values to verify consistency."

        return "NOT_APPLICABLE", None, f"Rule {rule_id} is not implemented or applicable."

    def run_compliance(self, product, scan_date="2026-09-06"):
        rule_results = {}
        applicable_count = 0
        
        for rule in self.rules:
            r_id = rule['rule_id']
            status, fail_code, msg = self.evaluate_rule(r_id, product, scan_date)
            if status != "NOT_APPLICABLE":
                rule_results[r_id] = {
                    "status": status,
                    "on_fail_code": fail_code,
                    "message": msg,
                    "severity": rule.get('severity', 'BLOCKER'),
                    "category": rule.get('category', 'COMPLETENESS')
                }
                applicable_count += 1
                
        has_blocker_fail = False
        has_major_fail = False
        has_review = False
        
        failed_rule_ids = []
        review_rule_ids = []
        
        for r_id, res in rule_results.items():
            if res['status'] == 'FAIL':
                failed_rule_ids.append(r_id)
                if res['severity'] == 'BLOCKER':
                    has_blocker_fail = True
                elif res['severity'] == 'MAJOR':
                    has_major_fail = True
            elif res['status'] == 'REVIEW':
                review_rule_ids.append(r_id)
                has_review = True
                
        if has_review:
            overall_verdict = "NEEDS_REVIEW"
        elif has_blocker_fail or has_major_fail:
            overall_verdict = "NON_COMPLIANT"
        else:
            overall_verdict = "COMPLIANT"
            
        return {
            "overall_verdict": overall_verdict,
            "rule_results": rule_results,
            "failed_rules": failed_rule_ids,
            "review_rules": review_rule_ids,
            "applicable_count": applicable_count
        }

if __name__ == '__main__':
    engine = ComplianceEngine()
    print("ComplianceEngine reference implementation initialized successfully.")
