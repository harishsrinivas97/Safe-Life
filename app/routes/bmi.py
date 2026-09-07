# app/routes/bmi.py
from flask import Blueprint, render_template, request
from app.utils.decorators import login_required

bmi_bp = Blueprint('bmi', __name__)


def calculate_bmi(weight: float, height_cm: float) -> tuple:
    """Calculate BMI and return (value, category, color)."""
    if height_cm <= 0 or weight <= 0:
        return None, 'Invalid input', 'danger'
    height_m = height_cm / 100
    bmi      = round(weight / (height_m ** 2), 1)
    if bmi < 18.5:
        return bmi, 'Underweight', 'warning'
    elif bmi < 25:
        return bmi, 'Normal Weight', 'success'
    elif bmi < 30:
        return bmi, 'Overweight', 'warning'
    else:
        return bmi, 'Obese', 'danger'


@bmi_bp.route('/bmi', methods=['GET', 'POST'])
@login_required
def calculator():
    bmi_value = category = color = None
    errors = []

    if request.method == 'POST':
        try:
            weight = float(request.form.get('weight', 0))
            height = float(request.form.get('height', 0))
            if weight <= 0 or height <= 0:
                raise ValueError
            bmi_value, category, color = calculate_bmi(weight, height)
        except (ValueError, ZeroDivisionError):
            errors.append('Please enter valid weight and height values.')

    return render_template(
        'bmi_calculator.html',
        bmi=bmi_value,
        category=category,
        color=color,
        errors=errors
    )
