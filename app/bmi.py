from flask import Blueprint, render_template, request
bmi_bp = Blueprint('bmi', __name__)

def calculate_bmi_logic(form_data):
    try:
        weight = float(form_data['weight'])
        height = float(form_data['height']) / 100  # cm to m
        bmi_value = round(weight / (height ** 2), 2)

        if bmi_value < 18.5:
            category = "Underweight"
        elif 18.5 <= bmi_value < 24.9:
            category = "Normal weight"
        elif 25 <= bmi_value < 29.9:
            category = "Overweight"
        else:
            category = "Obese"

        return bmi_value, category
    except Exception:
        return None, "Invalid input"

# ✅ Define the route using this blueprint
@bmi_bp.route('/bmi_calculator', methods=['GET', 'POST'])
def bmi_calculator():
    bmi = None
    category = None
    if request.method == 'POST':
        bmi, category = calculate_bmi_logic(request.form)
    return render_template('bmi_calculator.html', bmi=bmi, category=category)
