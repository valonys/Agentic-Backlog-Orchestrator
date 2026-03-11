"""
Generate sample test data for Backlog Inspector Dashboard
Run: python generate_test_data.py
"""
import openpyxl
from datetime import datetime, timedelta
import random

def generate_sample_data():
    """Generate sample Excel file for testing"""
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Base"
    
    # Headers
    headers = [
        "Tag", "Item Class", "Description", "Functional Location",
        "Last Insp/", "Freq/ (SAP)", "Next Insp/", "Year", "Due Date",
        "Compl/ date", "PMonth Insp", "CMonth Insp", "SECE STATUS",
        "Delay", "M. Item", "M. Plan", "Job Done", "Days in Backlog", "Backlog?"
    ]
    ws.append(headers)
    
    # Sample data
    systems = ["STRUC", "INERT", "HVAC", "FIRE", "UTIL", "ELEC"]
    locations = ["FPSOT", "FPSOH", "DECK"]
    item_classes = [
        "Corrosion Monitoring",
        "Flame Arrestor",
        "Pressure Relief Valve",
        "Fire Detector",
        "Emergency Lighting",
        "Structural Inspection"
    ]
    
    today = datetime.now()
    
    for i in range(50):
        tag = f"TA{1000 + i:04d}"
        system = random.choice(systems)
        location = random.choice(locations)
        item_class = random.choice(item_classes)
        
        # Random dates
        days_overdue = random.randint(0, 200)
        due_date = today - timedelta(days=days_overdue)
        last_insp = due_date - timedelta(days=365)
        
        # SECE status (30% chance)
        is_sece = random.random() < 0.3
        
        row = [
            tag,
            item_class,
            f"{item_class} inspection for {tag}",
            f"GIR/{location}/{system}/{tag}",
            last_insp.strftime("%d/%m/%Y"),
            "12",  # Monthly
            due_date.strftime("%d/%m/%Y"),
            str(due_date.year),
            due_date.strftime("%Y-%m-%d"),
            "0",
            str(due_date.month),
            str(today.month),
            "SCE" if is_sece else "",
            "< 6 Months" if days_overdue < 180 else "> 6 Months",
            f"300{25000 + i}",
            f"AOGIR{tag}",
            "Not Compl",
            days_overdue,
            "Yes"
        ]
        ws.append(row)
    
    # Save file
    filename = "sample_backlog_data.xlsx"
    wb.save(filename)
    print(f"✅ Generated {filename} with 50 sample backlog items")
    print(f"   - Mix of risk levels (High/Medium/Low)")
    print(f"   - Various systems: {', '.join(systems)}")
    print(f"   - Locations: {', '.join(locations)}")
    print(f"   - SECE items: ~30%")

if __name__ == "__main__":
    generate_sample_data()
