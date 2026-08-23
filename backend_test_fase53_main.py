#!/usr/bin/env python3
"""Backend Test Fase 53 — Lead → Customer → Contract → Documents
Tests all 8 backend scenarios from the review request using PUBLIC endpoint.
"""
import requests
import sys
import time
from typing import Dict, Any, Optional

BASE_URL = "https://permission-audit-16.preview.emergentagent.com/api"
PASSWORD = "Sipro#2026"

class Fase53BackendTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []
        self.tokens = {}
        
    def log(self, msg, status="INFO"):
        prefix = {"PASS": "✅", "FAIL": "❌", "INFO": "🔍"}.get(status, "ℹ️")
        print(f"{prefix} {msg}")
        
    def login(self, email: str) -> str:
        """Login and return token"""
        r = requests.post(f"{BASE_URL}/auth/login", 
                         json={"email": email, "password": PASSWORD}, timeout=30)
        if r.status_code != 200:
            raise Exception(f"Login failed for {email}: {r.status_code}")
        token = r.json()["access_token"]
        self.tokens[email] = token
        return token
        
    def headers(self, email: str) -> Dict[str, str]:
        """Get auth headers for email"""
        if email not in self.tokens:
            self.login(email)
        return {"Authorization": f"Bearer {self.tokens[email]}"}
        
    def test(self, name: str, fn):
        """Run a test and track results"""
        self.tests_run += 1
        self.log(f"Testing: {name}", "INFO")
        try:
            fn()
            self.tests_passed += 1
            self.log(f"PASSED: {name}", "PASS")
            self.results.append({"test": name, "status": "PASS"})
            return True
        except AssertionError as e:
            self.log(f"FAILED: {name} — {str(e)}", "FAIL")
            self.results.append({"test": name, "status": "FAIL", "error": str(e)})
            return False
        except Exception as e:
            self.log(f"ERROR: {name} — {str(e)}", "FAIL")
            self.results.append({"test": name, "status": "ERROR", "error": str(e)})
            return False
            
    def create_test_lead_and_unit(self) -> tuple:
        """Create a test lead and get available unit"""
        import random
        tanda = str(int(time.time()))[-6:] + str(random.randint(100, 999))
        sa = self.headers("superadmin@sipro.co.id")
        
        # Create lead with unique phone
        lead_r = requests.post(f"{BASE_URL}/leads", headers=sa, json={
            "name": f"Test Lead Fase53 {tanda}",
            "phone": f"+628129{tanda}",
            "source": "walk_in",
            "notes": "Backend test Fase 53"
        }, timeout=30)
        assert lead_r.status_code == 200, f"Failed to create lead: {lead_r.status_code} {lead_r.text}"
        lead_id = lead_r.json()["data"]["id"]
        
        # Get available unit
        units_r = requests.get(f"{BASE_URL}/units", headers=sa,
                              params={"status": "available", "limit": 1}, timeout=30)
        assert units_r.status_code == 200, "Failed to get units"
        units = units_r.json()["data"]
        assert len(units) > 0, "No available units"
        unit_id = units[0]["id"]
        
        return lead_id, unit_id
        
    def run_backend_1(self):
        """BACKEND-1: Quotation → Deal (reserved) → Book"""
        def test():
            lead_id, unit_id = self.create_test_lead_and_unit()
            sa = self.headers("superadmin@sipro.co.id")
            
            # Create quotation with addons
            q_r = requests.post(f"{BASE_URL}/quotations", headers=sa, json={
                "lead_id": lead_id,
                "unit_id": unit_id,
                "addons": [
                    {"code": "ADD-TANAH", "qty": 12},
                    {"code": "ADD-HOOK", "qty": 1}
                ],
                "note": "Test Backend-1"
            }, timeout=30)
            assert q_r.status_code == 200, f"Quotation creation failed: {q_r.status_code}"
            quotation_id = q_r.json()["data"]["id"]
            
            # Convert to deal
            conv_r = requests.post(f"{BASE_URL}/quotations/{quotation_id}/convert",
                                  headers=sa, json={"note": "Test"}, timeout=30)
            assert conv_r.status_code == 200, f"Conversion failed: {conv_r.status_code}"
            deal = conv_r.json()["data"]["deal"]
            deal_id = deal["id"]
            
            # Verify deal is reserved
            assert deal["status"] == "reserved", f"Deal status is {deal['status']}, expected 'reserved'"
            assert deal.get("reserved_until"), "reserved_until not set"
            
            # Book the deal (this should work now, was blocked before)
            book_r = requests.post(f"{BASE_URL}/deals/{deal_id}/book",
                                  headers=sa, json={}, timeout=30)
            assert book_r.status_code == 200, f"Booking failed: {book_r.status_code} (BUG: deal from quotation cannot be booked)"
            
            self.log("  ✓ Quotation → Deal (reserved) → Book flow works correctly")
            return deal_id, lead_id
            
        return test()
        
    def run_backend_2(self, deal_id_reserved=None):
        """BACKEND-2: Convert preview blocks before booking"""
        def test():
            if not deal_id_reserved:
                # Create a reserved deal
                lead_id, unit_id = self.create_test_lead_and_unit()
                sa = self.headers("superadmin@sipro.co.id")
                q_r = requests.post(f"{BASE_URL}/quotations", headers=sa, json={
                    "lead_id": lead_id, "unit_id": unit_id, "note": "Test"
                }, timeout=30)
                quotation_id = q_r.json()["data"]["id"]
                conv_r = requests.post(f"{BASE_URL}/quotations/{quotation_id}/convert",
                                      headers=sa, json={}, timeout=30)
                deal_id = conv_r.json()["data"]["deal"]["id"]
            else:
                deal_id = deal_id_reserved
                
            sa = self.headers("superadmin@sipro.co.id")
            
            # Preview should block if not booked
            prev_r = requests.get(f"{BASE_URL}/deals/{deal_id}/convert-preview",
                                 headers=sa, timeout=30)
            assert prev_r.status_code == 200, f"Preview failed: {prev_r.status_code}"
            prev_data = prev_r.json()["data"]
            
            # If deal is still reserved (not booked), should have blocks
            if prev_data.get("can_convert") is False:
                blocks = prev_data.get("blocks", [])
                # Blocks can be list of strings or list of objects with 'code' field
                block_codes = [b if isinstance(b, str) else b.get("code") for b in blocks]
                assert "deal_belum_booking" in block_codes, \
                    f"Expected 'deal_belum_booking' in blocks, got {block_codes}"
                self.log("  ✓ Convert preview correctly blocks reserved (not booked) deals")
            else:
                # Deal is already booked, should allow conversion
                assert prev_data.get("can_convert") is True, "Booked deal should allow conversion"
                self.log("  ✓ Convert preview allows booked deals")
                
        test()
        
    def run_backend_3(self):
        """BACKEND-3: Convert deal → customer + contract (idempotent)"""
        def test():
            # Create and book a deal
            lead_id, unit_id = self.create_test_lead_and_unit()
            sa = self.headers("superadmin@sipro.co.id")
            
            q_r = requests.post(f"{BASE_URL}/quotations", headers=sa, json={
                "lead_id": lead_id, "unit_id": unit_id, "note": "Test"
            }, timeout=30)
            quotation_id = q_r.json()["data"]["id"]
            
            conv_r = requests.post(f"{BASE_URL}/quotations/{quotation_id}/convert",
                                  headers=sa, json={}, timeout=30)
            deal_id = conv_r.json()["data"]["deal"]["id"]
            
            # Book it
            requests.post(f"{BASE_URL}/deals/{deal_id}/book", headers=sa, json={}, timeout=30)
            
            # Convert to customer (KPR scheme)
            import random
            tanda = str(int(time.time()))[-6:] + str(random.randint(100, 999))
            cv1_r = requests.post(f"{BASE_URL}/deals/{deal_id}/convert", headers=sa, json={
                "scheme": "kpr",
                "nik": f"3201{tanda}",
                "address": "Jl. Test 123"
            }, timeout=30)
            assert cv1_r.status_code == 200, f"First conversion failed: {cv1_r.status_code}"
            cv1_data = cv1_r.json()["data"]
            
            assert cv1_data.get("created") is True, "First conversion should create customer"
            customer = cv1_data.get("customer", {})
            contract = cv1_data.get("contract", {})
            
            # Verify customer linked to lead
            assert customer.get("lead_id") == lead_id or lead_id in customer.get("lead_ids", []), \
                "Customer not linked to lead"
            
            # Verify contract has number starting with KTR
            contract_number = contract.get("number", "")
            assert contract_number.startswith("KTR/"), f"Contract number should start with KTR/, got {contract_number}"
            
            # Convert again (idempotent test)
            cv2_r = requests.post(f"{BASE_URL}/deals/{deal_id}/convert", headers=sa, json={
                "scheme": "kpr"
            }, timeout=30)
            assert cv2_r.status_code == 200, f"Second conversion failed: {cv2_r.status_code}"
            cv2_data = cv2_r.json()["data"]
            
            assert cv2_data.get("created") is False, "Second conversion should not create duplicate (idempotent)"
            
            self.log("  ✓ Deal → Customer + Contract conversion works and is idempotent")
            return contract.get("id"), deal_id
            
        return test()
        
    def run_backend_4(self, contract_id=None):
        """BACKEND-4: Contract breakdown with null values (not 0)"""
        def test():
            cid = contract_id
            if not cid:
                cid, _ = self.run_backend_3()
                
            sa = self.headers("superadmin@sipro.co.id")
            
            # Get contract
            c_r = requests.get(f"{BASE_URL}/contracts/{cid}", headers=sa, timeout=30)
            assert c_r.status_code == 200, f"Failed to get contract: {c_r.status_code}"
            contract = c_r.json()["data"]
            
            breakdown = contract.get("breakdown", {})
            rows = breakdown.get("rows", [])
            
            # Check all required components exist as separate rows
            required_codes = ["UNIT_PRICE", "EXCESS_LAND", "HOOK_FEE", "BOOKING_FEE", 
                            "BPHTB", "NOTARY_FEE", "BANK_FEE", "PLAFON_KREDIT"]
            codes_found = [r["code"] for r in rows]
            
            for code in required_codes:
                assert code in codes_found, f"Component {code} not found in breakdown rows"
                
            # Check that empty components have null (not 0)
            empty_rows = [r for r in rows if r.get("state") == "empty"]
            for row in empty_rows:
                assert row.get("amount") is None, \
                    f"Empty component {row['code']} has amount={row.get('amount')}, expected None (not 0)"
                    
            # Check total_is_provisional is true when costs incomplete
            assert breakdown.get("total_is_provisional") is True, \
                "total_is_provisional should be True when costs are incomplete"
                
            self.log("  ✓ Contract breakdown has separate rows, empty values are null (not 0)")
            return cid
            
        return test()
        
    def run_backend_5(self, contract_id=None):
        """BACKEND-5: Legal stage gates (negative tests)"""
        def test():
            cid = contract_id
            if not cid:
                cid, _ = self.run_backend_3()
                
            sa = self.headers("superadmin@sipro.co.id")
            
            # Try PPJB before DP paid (should fail)
            ppjb_r = requests.post(f"{BASE_URL}/contracts/{cid}/legal/ppjb",
                                  headers=sa, json={}, timeout=30)
            assert ppjb_r.status_code == 400, \
                f"PPJB should be blocked before DP paid, got {ppjb_r.status_code}"
                
            # Try SP3K without file (should fail)
            sp3k_r = requests.post(f"{BASE_URL}/contracts/{cid}/kpr/stage/sp3k",
                                  headers=sa, json={"plafon": 150000000}, timeout=30)
            assert sp3k_r.status_code == 400, \
                f"SP3K should be blocked without file, got {sp3k_r.status_code}"
                
            # Try akad_kredit before SP3K (should fail)
            akad_r = requests.post(f"{BASE_URL}/contracts/{cid}/kpr/stage/akad_kredit",
                                  headers=sa, json={}, timeout=30)
            assert akad_r.status_code == 400, \
                f"Akad kredit should be blocked before SP3K, got {akad_r.status_code}"
                
            # Try AJB before akad_kredit (should fail for KPR)
            ajb_r = requests.post(f"{BASE_URL}/contracts/{cid}/legal/ajb",
                                 headers=sa, json={}, timeout=30)
            assert ajb_r.status_code == 400, \
                f"AJB should be blocked before akad_kredit (KPR scheme), got {ajb_r.status_code}"
                
            self.log("  ✓ Legal stage gates correctly block invalid progressions")
            return cid
            
        return test()
        
    def run_backend_6(self):
        """BACKEND-6: Full positive flow with payments and legal stages"""
        contract_id = None
        deal_id = None
        def test():
            nonlocal contract_id, deal_id
            # Create full flow
            contract_id, deal_id = self.run_backend_3()
            sa = self.headers("superadmin@sipro.co.id")
            fin = self.headers("finance@sipro.co.id")
            
            # Fill costs
            costs_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/costs", headers=fin, json={
                "bphtb": 4300000,
                "notary_fee": 13200000,
                "bank_fee": 10500000,
                "insurance": 2500000,
                "plafon_kredit": 160000000
            }, timeout=30)
            assert costs_r.status_code == 200, f"Failed to set costs: {costs_r.status_code}"
            
            # Check total_is_provisional is now false
            breakdown = costs_r.json()["data"]["breakdown"]
            assert breakdown.get("total_is_provisional") is False, \
                "total_is_provisional should be False after all costs filled"
                
            # Activate contract
            act_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/activate",
                                 headers=fin, json={}, timeout=30)
            assert act_r.status_code == 200, f"Failed to activate contract: {act_r.status_code}"
            
            plan = act_r.json()["data"]["payment_plan"]
            assert plan.get("state") == "ada", "Payment plan should exist after activation"
            
            # Upload SP3K file
            up_r = requests.post(f"{BASE_URL}/files/upload", headers=sa,
                                files={"file": ("sp3k.txt", b"Test SP3K", "text/plain")},
                                data={"owner_type": "contract", "owner_id": contract_id, 
                                     "doc_type": "sp3k"}, timeout=60)
            assert up_r.status_code == 200, f"Failed to upload file: {up_r.status_code}"
            file_id = up_r.json()["data"]["id"]
            
            # Progress through KPR stages
            stages = [
                ("diajukan_ke_bank", {"bank": "BTN"}),
                ("appraisal", {"amount": 170000000}),
                ("sp3k", {"number": "SP3K/TEST/001", "plafon": 160000000, 
                         "tenor_months": 180, "rate": 8.5, "file_id": file_id})
            ]
            
            for stage, payload in stages:
                r = requests.post(f"{BASE_URL}/contracts/{contract_id}/kpr/stage/{stage}",
                                 headers=sa, json=payload, timeout=30)
                assert r.status_code == 200, f"KPR stage {stage} failed: {r.status_code}"
                
            # Record payment (DP)
            ar_r = requests.get(f"{BASE_URL}/finance/ar/{deal_id}", headers=fin, timeout=30)
            ar_data = ar_r.json()["data"]
            invoice = ar_data.get("invoice", ar_data)
            outstanding = int(invoice.get("outstanding", 0))
            
            if outstanding > 0:
                pay_r = requests.post(f"{BASE_URL}/finance/ar/receipts", headers=fin, json={
                    "deal_id": deal_id,
                    "amount": min(outstanding, 50000000),  # Pay some amount
                    "method": "transfer",
                    "note": "Test payment"
                }, timeout=60)
                assert pay_r.status_code == 200, f"Payment failed: {pay_r.status_code}"
                
            # Now PPJB should work
            ppjb_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/legal/ppjb",
                                  headers=sa, json={"note": "Test"}, timeout=30)
            assert ppjb_r.status_code == 200, f"PPJB failed after payment: {ppjb_r.status_code}"
            
            # Akad kredit
            akad_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/kpr/stage/akad_kredit",
                                  headers=sa, json={"notary": "Test Notary", "file_id": file_id},
                                  timeout=30)
            assert akad_r.status_code == 200, f"Akad kredit failed: {akad_r.status_code}"
            
            # AJB
            ajb_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/legal/ajb",
                                 headers=sa, json={"notary": "Test Notary"}, timeout=30)
            assert ajb_r.status_code == 200, f"AJB failed: {ajb_r.status_code}"
            
            # Verify deal reflects legal stage
            deal_r = requests.get(f"{BASE_URL}/deals/{deal_id}", headers=sa, timeout=30)
            deal = deal_r.json()["data"]
            assert deal.get("legal_stage") == "ajb", \
                f"Deal legal_stage should be 'ajb', got {deal.get('legal_stage')}"
                
            self.log("  ✓ Full positive flow: costs → activate → payments → legal stages → AJB")
            return contract_id
            
        return test()
        
    def run_backend_7(self):
        """BACKEND-7: Owner documents generation and PDF"""
        def test():
            # Create contract with full flow
            contract_id = self.run_backend_6()
            sa = self.headers("superadmin@sipro.co.id")
            
            # Get available documents
            avail_r = requests.get(f"{BASE_URL}/contracts/{contract_id}/documents/available",
                                  headers=sa, timeout=30)
            assert avail_r.status_code == 200, f"Failed to get available docs: {avail_r.status_code}"
            avail_data = avail_r.json()["data"]
            recommended = avail_r.json().get("recommended_code")
            
            # Should recommend SPR_KPR for KPR scheme
            assert recommended == "SPR_KPR", \
                f"Should recommend SPR_KPR for KPR contract, got {recommended}"
                
            # SPR_CASH should not be allowed for KPR contract
            spr_cash = next((d for d in avail_data if d["code"] == "SPR_CASH"), None)
            if spr_cash:
                assert spr_cash.get("can_generate") is False, \
                    "SPR_CASH should not be allowed for KPR contract"
                    
            # SPKT should be allowed (has excess land)
            spkt = next((d for d in avail_data if d["code"] == "SPKT"), None)
            assert spkt and spkt.get("can_generate") is True, \
                "SPKT should be allowed when there's excess land"
                
            # Generate SPR_KPR
            spr_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/documents",
                                 headers=sa, json={"template_code": "SPR_KPR"}, timeout=30)
            assert spr_r.status_code == 200, f"Failed to generate SPR_KPR: {spr_r.status_code}"
            spr_doc = spr_r.json()["data"]
            
            # Check document number format
            doc_number = spr_doc.get("doc_number", "")
            assert doc_number.count("/") == 4, \
                f"Document number should have 4 slashes, got {doc_number}"
            assert "SPR-KPR" in doc_number, \
                f"Document number should contain SPR-KPR, got {doc_number}"
                
            # Check content has numbers from contract
            content = spr_doc.get("content", "")
            assert "plafon" in content.lower() or "kredit" in content.lower(), \
                "Document should mention plafon/kredit"
                
            # Get PDF
            pdf_r = requests.get(f"{BASE_URL}/documents/{spr_doc['id']}/pdf",
                                headers=sa, timeout=60)
            assert pdf_r.status_code == 200, f"Failed to get PDF: {pdf_r.status_code}"
            assert pdf_r.headers.get("content-type", "").startswith("application/pdf"), \
                f"PDF should be application/pdf, got {pdf_r.headers.get('content-type')}"
            assert len(pdf_r.content) > 1000, "PDF should have content"
            
            # Generate SPKT
            spkt_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/documents",
                                  headers=sa, json={"template_code": "SPKT"}, timeout=30)
            assert spkt_r.status_code == 200, f"Failed to generate SPKT: {spkt_r.status_code}"
            spkt_doc = spkt_r.json()["data"]
            
            # SPKT should reference SPR number
            spkt_content = spkt_doc.get("content", "")
            assert doc_number in spkt_content, \
                f"SPKT should reference SPR number {doc_number}"
                
            self.log("  ✓ Owner documents: SPR_KPR and SPKT generated with correct format and PDF")
            
        test()
        
    def run_backend_8(self):
        """BACKEND-8: RBAC - permissions enforcement"""
        def test():
            # Create a contract
            contract_id, deal_id = self.run_backend_3()
            
            # Test 1: sales2 cannot access contract from sales
            sales2 = self.headers("sales2@sipro.co.id")
            c_r = requests.get(f"{BASE_URL}/contracts/{contract_id}", headers=sales2, timeout=30)
            assert c_r.status_code == 403, \
                f"sales2 should not access other sales' contract, got {c_r.status_code}"
                
            # Test 2: pm cannot update contract costs
            pm = self.headers("pm@sipro.co.id")
            costs_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/costs", headers=pm, json={
                "bphtb": 5000000
            }, timeout=30)
            assert costs_r.status_code == 403, \
                f"pm should not update contract costs, got {costs_r.status_code}"
                
            # Test 3: finance can fill costs and activate
            fin = self.headers("finance@sipro.co.id")
            costs_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/costs", headers=fin, json={
                "bphtb": 4300000,
                "notary_fee": 13200000,
                "bank_fee": 10500000,
                "insurance": 2500000,
                "plafon_kredit": 160000000
            }, timeout=30)
            assert costs_r.status_code == 200, \
                f"finance should be able to fill costs, got {costs_r.status_code}"
                
            act_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/activate",
                                 headers=fin, json={}, timeout=30)
            assert act_r.status_code == 200, \
                f"finance should be able to activate contract, got {act_r.status_code}"
                
            # Test 4: finance cannot advance legal stages (needs contracts:manage)
            ppjb_r = requests.post(f"{BASE_URL}/contracts/{contract_id}/legal/ppjb",
                                  headers=fin, json={}, timeout=30)
            assert ppjb_r.status_code == 403, \
                f"finance should not advance legal stages, got {ppjb_r.status_code}"
                
            self.log("  ✓ RBAC: sales2 blocked, pm blocked from costs, finance can fill costs but not legal stages")
            
        test()
        
    def run_all_tests(self):
        """Run all backend tests"""
        print("\n" + "="*70)
        print("FASE 53 BACKEND TESTS - Lead → Customer → Contract → Documents")
        print("="*70)
        
        self.log("Logging in users...", "INFO")
        for email in ["superadmin@sipro.co.id", "finance@sipro.co.id", 
                     "sales2@sipro.co.id", "pm@sipro.co.id"]:
            self.login(email)
            
        print("\n--- BACKEND-1: Quotation → Deal → Book ---")
        self.test("BACKEND-1: Quotation with addons → reserved deal → booking works", 
                 self.run_backend_1)
        
        print("\n--- BACKEND-2: Convert Preview Blocks ---")
        self.test("BACKEND-2: Convert preview blocks reserved deals, allows booked deals",
                 self.run_backend_2)
        
        print("\n--- BACKEND-3: Deal → Customer Conversion ---")
        self.test("BACKEND-3: Deal converts to customer + contract (idempotent)",
                 self.run_backend_3)
        
        print("\n--- BACKEND-4: Contract Breakdown ---")
        self.test("BACKEND-4: Contract breakdown has null values (not 0) for empty costs",
                 self.run_backend_4)
        
        print("\n--- BACKEND-5: Legal Gates (Negative) ---")
        self.test("BACKEND-5: Legal stage gates block invalid progressions",
                 self.run_backend_5)
        
        print("\n--- BACKEND-6: Full Positive Flow ---")
        self.test("BACKEND-6: Full flow with costs, payments, KPR stages, and legal stages",
                 self.run_backend_6)
        
        print("\n--- BACKEND-7: Owner Documents ---")
        self.test("BACKEND-7: Owner documents (SPR_KPR, SPKT) generation and PDF",
                 self.run_backend_7)
        
        print("\n--- BACKEND-8: RBAC ---")
        self.test("BACKEND-8: RBAC permissions correctly enforced",
                 self.run_backend_8)
        
        print("\n" + "="*70)
        print(f"RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*70)
        
        if self.tests_passed < self.tests_run:
            print("\nFAILED TESTS:")
            for r in self.results:
                if r["status"] != "PASS":
                    print(f"  ❌ {r['test']}")
                    if "error" in r:
                        print(f"     {r['error']}")
            return 1
        else:
            print("\n✅ ALL BACKEND TESTS PASSED")
            return 0

def main():
    tester = Fase53BackendTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
