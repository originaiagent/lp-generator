
import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from modules.data_store import DataStore

class TestDataStorePersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("data/uploads/test_product")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.product_id = "test_prod_123"

    def test_smart_merge_logic(self):
        """Test that local lists are preserved when DB returns None"""
        
        # 1. Setup Local Data (Has Images and URL)
        local_data = {
            "id": self.product_id,
            "name": "Local Product",
            "product_images": ["/path/to/img1.png", "/path/to/img2.png"],
            "reference_lp_image_urls": ["https://supa.base/img1.png"]
        }
        
        # Create a dummy file
        with patch.object(DataStore, '__init__', return_value=None) as mock_init:
            ds = DataStore()
            ds.data_dir = Path("data/products") # Mock directory
            ds.use_supabase = True
            ds.base_url = "https://mock.supabase.co"
            ds.headers = {}
            
            # Mock _get_from_supabase to return data WITHOUT images (Simulation of the bug)
            db_data = {
                "id": self.product_id,
                "name": "DB Product", # Name might be updated in DB
                "product_images": None, # DB has NULL/Empty
                "reference_lp_image_urls": None 
            }
            ds._get_from_supabase = MagicMock(return_value=db_data)
            
            # Mock file reading
            with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(local_data))):
                with patch("pathlib.Path.exists", return_value=True):
                    
                    # RUN THE METHOD UNDER TEST
                    merged = ds.get_product(self.product_id)
                    
                    print("\n--- Test Results ---")
                    print(f"DB Input (Images): {db_data['product_images']}")
                    print(f"Local Input (Images): {local_data['product_images']}")
                    print(f"Merged Result (Images): {merged.get('product_images')}")
                    
                    # VERIFY
                    self.assertEqual(merged["name"], "DB Product", "Should prioritize DB for simple fields")
                    self.assertEqual(merged["product_images"], local_data["product_images"], "Should use Local for protected list fields if DB is None")
                    self.assertEqual(merged["reference_lp_image_urls"], local_data["reference_lp_image_urls"], "Should use Local for protected list fields")
                    
                    print("✅ Smart Merge logic verified: Local lists preserved.")

if __name__ == "__main__":
    unittest.main()
