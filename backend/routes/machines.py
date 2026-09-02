from flask import Blueprint, request, jsonify
from models import Machine, db

machines_bp = Blueprint("machines", __name__)


@machines_bp.route("/", methods=["GET"])
def list_machines():
    brand = request.args.get("brand")
    category = request.args.get("category")
    query = Machine.query
    if brand:
        query = query.filter(Machine.brand == brand)
    if category:
        query = query.filter(Machine.category == category)
    machines = query.order_by(Machine.category, Machine.name).all()
    return jsonify({"machines": [m.to_dict() for m in machines]}), 200


@machines_bp.route("/<int:machine_id>", methods=["GET"])
def get_machine(machine_id):
    machine = db.session.get(Machine, machine_id)
    if not machine:
        return jsonify({"error": "Machine introuvable"}), 404
    return jsonify({"machine": machine.to_dict()}), 200