from flask import Blueprint, jsonify
from repositories.conv_repo import ConversationRepository

bp = Blueprint("conv_bp", __name__)
repo = ConversationRepository()


@bp.route("/conversations", methods=["GET"])
def list_conversations():
    return jsonify(repo.list_all())


@bp.route("/conversations", methods=["POST"])
def create_conversation():
    conv_id = repo.create()
    return jsonify({"id": conv_id, "titre": "Nouvelle conversation"})


@bp.route("/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    repo.delete(conv_id)
    return jsonify({"status": "ok"})


@bp.route("/conversations/<conv_id>/messages", methods=["GET"])
def get_messages(conv_id):
    msgs = repo.get_messages(conv_id)
    return jsonify({"messages": msgs})
