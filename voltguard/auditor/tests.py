from django.test import TestCase, RequestFactory
from auditor.views import export_pdf
from auditor.models import Appliance, Project
from auditor.engine import (
    calculate_current,
    select_mcb,
    select_wire_gauge,
    calculate_voltage_drop,
    balance_phases
)

class EngineTests(TestCase):
    
    def test_calculate_current(self):
        self.assertEqual(calculate_current(2300, voltage=230), 10.0)
        self.assertAlmostEqual(calculate_current(1500, voltage=230), 6.52, places=2)
        
    def test_select_mcb(self):
        # I = 10A -> Safety I = 12.5A -> nearest standard > 12.5 is 16A
        self.assertEqual(select_mcb(10.0)[0], 16)
        # I = 20A -> Safety I = 25A -> nearest standard is 25A
        self.assertEqual(select_mcb(20.0)[0], 25)
        # I = 35A -> Safety I = 43.75 -> nearest standard is 63A
        self.assertEqual(select_mcb(35.0)[0], 63)
        # Test MCB Types
        self.assertEqual(select_mcb(10.0, 'Motor/AC')[1], 'C')
        self.assertEqual(select_mcb(10.0, 'Light')[1], 'B')
        
    def test_select_wire_gauge(self):
        # 10A should return minimum 1.5mm2
        self.assertEqual(select_wire_gauge(10.0)[0], 1.5)
        # 20A should return 2.5mm2
        self.assertEqual(select_wire_gauge(20.0)[0], 2.5)
        
    def test_calculate_voltage_drop(self):
        # L=20m, I=10A, gauge=1.5, R=12.1 (1.5mm2) -> V_drop = (2 * 20 * 10 * 12.1) / 1000 = 4.84V
        v_drop, percent, is_fail, warning, upgrade = calculate_voltage_drop(20, 10, 1.5, 12.1, 230)
        self.assertAlmostEqual(v_drop, 4.84)
        self.assertAlmostEqual(percent, (4.84/230)*100, places=2)
        self.assertFalse(is_fail) # 4.84V / 230V = 2.1% < 3.0%
        
    def test_balance_phases(self):
        project = Project.objects.create(name="Test")
        app1 = Appliance.objects.create(project=project, name="AC 1", power_watts=3000, length_m=10)
        app2 = Appliance.objects.create(project=project, name="AC 2", power_watts=3000, length_m=10)
        app3 = Appliance.objects.create(project=project, name="Heater", power_watts=5000, length_m=10)
        
        # Total Power = 11000W (>7kW) so it SHOULD balance phases
        appliances = [app1, app2, app3]
        result = balance_phases(appliances)
        
        self.assertTrue(result['requires_3_phase'])
        # Heater (5000) goes to R
        # AC 1 (3000) goes to Y
        # AC 2 (3000) goes to B
        self.assertEqual(result['Loads']['L2'], 3000)
        self.assertEqual(result['Loads']['L3'], 3000)

class ViewTests(TestCase):
    def test_export_pdf_view(self):
        project = Project.objects.create(name="Test")
        Appliance.objects.create(project=project, name="AC 1", power_watts=3000, power_factor=0.8, length_m=10)
        
        factory = RequestFactory()
        request = factory.get('/export/')
        request.COOKIES['vg_uid'] = 'dummy_test_uid'
        # Crucial for views.py
        project.user_uid = 'dummy_test_uid'
        project.save()
        
        try:
            response = export_pdf(request)
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
