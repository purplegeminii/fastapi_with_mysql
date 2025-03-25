import unittest
import requests
import json

# Base URL for the FastAPI application
BASE_URL = "http://localhost:8000"

class TestTodoAPI(unittest.TestCase):
    def setUp(self):
        # Create a test item that we can use for getting and deleting
        self.test_item = {
            "todotext": "Test item",
            "is_done": False
        }
        response = requests.post(f"{BASE_URL}/items", json=self.test_item)
        self.assertEqual(response.status_code, 200)
        self.test_item_id = response.json()["item_id"]
    
    def test_root_endpoint(self):
        response = requests.get(BASE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"hello": "world"})
    
    def test_create_item(self):
        new_item = {
            "todotext": "Buy groceries",
            "is_done": False
        }
        response = requests.post(f"{BASE_URL}/items", json=new_item)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("item_id", data)
        self.assertEqual(data["todotext"], new_item["todotext"])
        self.assertEqual(data["is_done"], new_item["is_done"])
        
        # Clean up - delete the created item
        requests.delete(f"{BASE_URL}/items/{data['item_id']}")
    
    def test_list_items(self):
        response = requests.get(f"{BASE_URL}/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        
        # Test with limit parameter
        response = requests.get(f"{BASE_URL}/items?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data), 5)
    
    def test_get_item(self):
        # Get the item created in setUp
        response = requests.get(f"{BASE_URL}/items/{self.test_item_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["item_id"], self.test_item_id)
        self.assertEqual(data["todotext"], self.test_item["todotext"])
        self.assertEqual(data["is_done"], self.test_item["is_done"])
        
        # Test getting non-existent item
        response = requests.get(f"{BASE_URL}/items/9999")
        self.assertEqual(response.status_code, 404)
    
    def test_delete_item(self):
        # Create an item to delete
        new_item = {
            "todotext": "Item to delete",
            "is_done": False
        }
        response = requests.post(f"{BASE_URL}/items", json=new_item)
        self.assertEqual(response.status_code, 200)
        item_id = response.json()["item_id"]
        
        # Delete the item
        response = requests.delete(f"{BASE_URL}/items/{item_id}")
        self.assertEqual(response.status_code, 200)
        
        # Verify the item is deleted
        response = requests.get(f"{BASE_URL}/items/{item_id}")
        self.assertEqual(response.status_code, 404)
        
        # Test deleting non-existent item
        response = requests.delete(f"{BASE_URL}/items/9999")
        self.assertEqual(response.status_code, 404)
    
    def tearDown(self):
        # Delete the test item created in setUp
        requests.delete(f"{BASE_URL}/items/{self.test_item_id}")

if __name__ == "__main__":
    # Make sure your FastAPI server is running before executing tests
    print("Make sure your FastAPI server is running on http://localhost:8000")
    unittest.main()