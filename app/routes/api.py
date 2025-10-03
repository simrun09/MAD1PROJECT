from functools import wraps
from flask import Blueprint, jsonify, request, abort
from app.models import Users, Services, ServiceRequests

api_bp = Blueprint('api', __name__)

@api_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "success": False,
        "error": 401,
        "message": error.description or "Unauthorized"
    }), 401

# --- API Authentication Decorator ---
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('x-api-key') # Standard header for API keys
        if not api_key:
            abort(401, description="API key is missing.") # Unauthorized
        
        user = Users.query.filter_by(api_key=api_key).first()
        if not user:
            abort(401, description="Invalid API key.") # Unauthorized
        
        return f(user, *args, **kwargs) # Pass the authenticated user to the route
    return decorated_function

# --- Public Endpoints ---

@api_bp.route('/services', methods=['GET'])
def get_services():
    """Returns a list of all available services."""
    services = Services.query.order_by(Services.service_type).all()
    results = [
        {'id': s.id, 'name': s.service_type, 'description': s.description, 'base_price': s.base_price}
        for s in services
    ]
    return jsonify(services=results)

# --- Protected Endpoints ---

@api_bp.route('/me', methods=['GET'])
@require_api_key
def get_me(user):
    """Returns the details of the authenticated user."""
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'address': user.address,
        'pin': user.pin
    }
    return jsonify(user=user_data)

@api_bp.route('/my-requests', methods=['GET'])
@require_api_key
def get_my_requests(user):
    """
    Returns a list of service requests for the authenticated user.
    Handles both customers and professionals.
    """
    if user.role == 'customer' and user.customer:
        requests = ServiceRequests.query.filter_by(customer_id=user.customer.id).all()
    elif user.role == 'professional' and user.professional:
        requests = ServiceRequests.query.filter_by(professional_id=user.professional.id).all()
    else:
        return jsonify(requests=[])

    results = []
    for req in requests:
        req_data = {
            'id': req.id,
            'service': req.service.service_type,
            'status': req.service_status.name,
            'proposed_price': req.proposed_price,
            'date_requested': req.date_of_request.isoformat(),
            'customer': req.customer.user.username,
            'professional': req.professional.user.username if req.professional else None
        }
        results.append(req_data)
        
    return jsonify(requests=results)