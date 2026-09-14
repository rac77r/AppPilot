from ubuntu_app_manager.services.inventory import InventoryService


def test_inventory_discovers_without_crashing():
    service = InventoryService()
    results = service.discover()
    assert isinstance(results, list)
