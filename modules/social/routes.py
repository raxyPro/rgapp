from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required

from extensions import db
from modules.chat.permissions import module_required
from modules.chat.util import get_current_user_id
from modules.cv.models import RBCVFile
from modules.cv.util import sanitize_filename
from modules.social.models import SocialLike, SocialPost
from models import RBUser, RBUserProfile

social_bp = Blueprint(
    "social",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/social",
)


def _uploads_root() -> Path:
    cfg = current_app.config.get("SOCIAL_UPLOAD_DIR") if current_app else None
    if cfg:
        return Path(cfg)
    return Path(current_app.root_path).parent / "uploads" / "social"


def _user_upload_dir(user_id: int) -> Path:
    d = _uploads_root() / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _allowed_image(fname: str) -> bool:
    fn = (fname or "").lower()
    return fn.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))


@social_bp.get("/")
@login_required
@module_required("social")
def index():
    me_id = get_current_user_id()
    users = {u.user_id: u for u in RBUser.query.all()}
    profiles = {p.user_id: p for p in RBUserProfile.query.filter(RBUserProfile.user_id.in_(users.keys())).all()}
    for uid, u in users.items():
        prof = profiles.get(uid)
        if prof:
            u.handle = getattr(prof, "handle", None)
    cv_files = RBCVFile.query.filter_by(owner_user_id=me_id, is_archived=False).order_by(RBCVFile.updated_at.desc()).all()

    roots = (
        SocialPost.query
        .filter(SocialPost.parent_id.is_(None))
        .order_by(SocialPost.created_at.desc())
        .all()
    )
    replies_by_parent = {}
    if roots:
        parent_ids = [r.post_id for r in roots]
        replies = (
            SocialPost.query
            .filter(SocialPost.parent_id.in_(parent_ids))
            .order_by(SocialPost.created_at.asc())
            .all()
        )
        for r in replies:
            replies_by_parent.setdefault(r.parent_id, []).append(r)

    all_ids = [r.post_id for r in roots]
    for rep_list in replies_by_parent.values():
        all_ids.extend([x.post_id for x in rep_list])

    likes_count = {}
    user_likes = set()
    if all_ids:
        like_rows = (
            db.session.query(SocialLike.post_id, db.func.count(SocialLike.like_id))
            .filter(SocialLike.post_id.in_(all_ids))
            .group_by(SocialLike.post_id)
            .all()
        )
        likes_count = {pid: cnt for pid, cnt in like_rows}

        mine = (
            db.session.query(SocialLike.post_id)
            .filter(SocialLike.post_id.in_(all_ids), SocialLike.user_id == me_id)
            .all()
        )
        user_likes = {pid for (pid,) in mine}

    return render_template(
        "social/index.html",
        roots=roots,
        replies_by_parent=replies_by_parent,
        users=users,
        me_id=me_id,
        cv_files=cv_files,
        likes_count=likes_count,
        user_likes=user_likes,
    )


@social_bp.post("/new")
@login_required
@module_required("social")
def new_post():
    me_id = get_current_user_id()
    body = (request.form.get("body") or "").strip()
    parent_id = request.form.get("parent_id")
    parent_id = int(parent_id) if parent_id and str(parent_id).isdigit() else None
    cvfile_id = None  # attachments removed

    if not body:
        flash("Message is required.", "danger")
        return redirect(url_for("social.index"))

    image_path = None  # attachments removed

    p = SocialPost(
        user_id=me_id,
        parent_id=parent_id,
        body=body,
        image_path=image_path,
        cvfile_id=cvfile_id,
    )
    db.session.add(p)
    db.session.commit()
    flash("Message posted.", "success")
    return redirect(url_for("social.index"))


@social_bp.post("/delete/<int:post_id>")
@login_required
@module_required("social")
def delete_post(post_id: int):
    me_id = get_current_user_id()
    p = SocialPost.query.get_or_404(post_id)
    me = RBUser.query.get(me_id)
    if p.user_id != me_id and not (me and me.is_admin):
        abort(403)

    # Remove uploaded file
    try:
        if p.image_path and os.path.exists(p.image_path):
            os.remove(p.image_path)
    except Exception:
        pass

    db.session.delete(p)
    db.session.commit()
    flash("Message deleted.", "info")
    return redirect(url_for("social.index"))


@social_bp.post("/like/<int:post_id>")
@login_required
@module_required("social")
def toggle_like(post_id: int):
    me_id = get_current_user_id()
    post = SocialPost.query.get_or_404(post_id)
    existing = SocialLike.query.filter_by(post_id=post_id, user_id=me_id).first()
    if existing:
        db.session.delete(existing)
        flash("Like removed.", "info")
    else:
        db.session.add(SocialLike(post_id=post_id, user_id=me_id))
        flash("Liked.", "success")
    db.session.commit()
    # Redirect back to feed
    return redirect(url_for("social.index"))


@social_bp.get("/uploads/<int:user_id>/<path:filename>")
@login_required
@module_required("social")
def uploaded_file(user_id: int, filename: str):
    # Security: serve only from social upload dir for the current user or admin
    me_id = get_current_user_id()
    me = RBUser.query.get(me_id)
    if user_id != me_id and not (me and me.is_admin):
        abort(403)
    directory = _user_upload_dir(user_id)
    return current_app.send_from_directory(directory, filename)
