# -*- coding: utf-8 -*-
"""
Dolcèra — Application de gestion des ventes, charges et dashboard.
Lancer avec : python app.py
Puis ouvrir : http://localhost:5000
"""
import sqlite3
import os
import io
import csv
import uuid
from datetime import date, timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, g, Response, flash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "dolcera.db")

app = Flask(__name__)
app.secret_key = "dolcera-secret-key-change-if-needed"

CATS = ["Cheesecake", "Tiramisu", "Cake", "Zouza", "Fondant", "Moelleux"]
CAT_COLORS = {
    "Cheesecake": "#1B4496", "Tiramisu": "#28569F", "Cake": "#E9A72F",
    "Zouza": "#C97F17", "Fondant": "#5F8FD9", "Moelleux": "#0F2E66"
}
CHARGE_CATS = ["Matières premières", "Emballages", "Loyer", "Salaires",
               "Électricité & Eau", "Transport / Livraison", "Marketing",
               "Maintenance", "Autre"]
GLOVO_MARKUP = 1.20       # +20% HT vs prix magasin
GLOVO_COMMISSION = 0.238  # 23.8% pris par Glovo

SEED_PRODUCTS = [
    ("Cheesecake", "Citron", 12.000, "unite"), ("Cheesecake", "Caramel", 9.000, "unite"),
    ("Cheesecake", "Caramel Noix de Pécan", 15.000, "unite"), ("Cheesecake", "Pistache", 15.000, "unite"),
    ("Cheesecake", "Nutella", 14.000, "unite"), ("Cheesecake", "Nutella Noisette Praliné", 15.000, "unite"),
    ("Cheesecake", "Nature", 7.000, "unite"),
    ("Tiramisu", "Classic", 12.000, "unite"), ("Tiramisu", "Citron", 14.000, "unite"), ("Tiramisu", "Pistache", 16.000, "unite"),
    ("Cake", "Vanille", 6.000, "unite"), ("Cake", "Marbré", 7.000, "unite"), ("Cake", "Cacao", 8.000, "unite"),
    ("Cake", "Citron", 8.000, "unite"), ("Cake", "Vanille GF", 10.000, "unite"), ("Cake", "Marbré GF", 11.000, "unite"),
    ("Cake", "Cacao GF", 12.000, "unite"), ("Cake", "Citron GF", 12.000, "unite"),
    ("Zouza", "Caramel", 30.000, "unite"), ("Zouza", "Caramel Noisette", 45.000, "unite"),
    ("Fondant", "Chocolat", 4.000, "unite"), ("Fondant", "Nutella", 6.000, "unite"), ("Fondant", "Nutella Banane", 8.000, "unite"),
    ("Fondant", "Noisette", 6.000, "unite"), ("Fondant", "Noisette Nutella", 7.500, "unite"), ("Fondant", "Amande", 5.000, "unite"),
    ("Fondant", "Amande Nutella", 6.500, "unite"), ("Fondant", "Pistache", 8.000, "unite"), ("Fondant", "Pistache Framboise", 9.000, "unite"),
    ("Moelleux", "Chocolat", 25.000, "kg"), ("Moelleux", "Nutella", 55.000, "kg"), ("Moelleux", "Nutella Banane", 50.000, "kg"),
    ("Moelleux", "Noisette", 50.000, "kg"), ("Moelleux", "Noisette Nutella", 60.000, "kg"), ("Moelleux", "Amande", 40.000, "kg"),
    ("Moelleux", "Amande Nutella", 50.000, "kg"), ("Moelleux", "Pistache", 65.000, "kg"), ("Moelleux", "Pistache Framboise", 90.000, "kg"),
    ("Moelleux", "Variés", 60.000, "kg"),
]

# ---------------------------------------------------------------- DB helpers
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""CREATE TABLE IF NOT EXISTS products(
        id TEXT PRIMARY KEY, category TEXT, name TEXT, price REAL, unit TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS sales_store(
        id TEXT PRIMARY KEY, date TEXT, product_id TEXT, product_name TEXT,
        category TEXT, unit TEXT, qty REAL, unit_price REAL, total REAL, created_at TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS sales_glovo(
        id TEXT PRIMARY KEY, date TEXT, product_id TEXT, product_name TEXT,
        category TEXT, unit TEXT, qty REAL, store_price REAL, glovo_price REAL,
        brut REAL, commission REAL, net REAL, status TEXT, created_at TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS charges(
        id TEXT PRIMARY KEY, date TEXT, category TEXT, description TEXT, amount REAL, created_at TEXT)""")
    count = db.execute("SELECT COUNT(*) c FROM products").fetchone()[0]
    if count == 0:
        for cat, name, price, unit in SEED_PRODUCTS:
            db.execute("INSERT INTO products(id,category,name,price,unit) VALUES (?,?,?,?,?)",
                       (str(uuid.uuid4()), cat, name, price, unit))
    db.commit()
    db.close()

# ---------------------------------------------------------------- utils
def today_iso():
    return date.today().isoformat()

def fr_date(iso):
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"

def dt(n):
    return f"{n:,.3f}".replace(",", " ").replace(".", ",") + " DT"

def period_range():
    preset = request.args.get("period", "month")
    today = date.today()
    if preset == "today":
        start = today
    elif preset == "7d":
        start = today - timedelta(days=6)
    elif preset == "month":
        start = today.replace(day=1)
    elif preset == "year":
        start = today.replace(month=1, day=1)
    elif preset == "all":
        start = date(2000, 1, 1)
    elif preset == "custom":
        s = request.args.get("start")
        e = request.args.get("end")
        start = date.fromisoformat(s) if s else today - timedelta(days=6)
        end = date.fromisoformat(e) if e else today
        return preset, start.isoformat(), end.isoformat()
    else:
        start = today.replace(day=1)
    return preset, start.isoformat(), today.isoformat()

def date_series(start, end):
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    out = []
    cur = d0
    guard = 0
    while cur <= d1 and guard < 400:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
        guard += 1
    return out

def top_n(d, n):
    return sorted(d.items(), key=lambda kv: -kv[1])[:n]

# ---------------------------------------------------------------- stats
def compute_magasin_stats(start, end):
    db = get_db()
    rows = db.execute("SELECT * FROM sales_store WHERE date>=? AND date<=? ORDER BY date DESC, created_at DESC",
                       (start, end)).fetchall()
    ca = sum(r["total"] for r in rows)
    by_cat, by_product, by_date = {}, {}, {}
    for r in rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + r["total"]
        by_product[r["product_name"]] = by_product.get(r["product_name"], 0) + r["total"]
        by_date[r["date"]] = by_date.get(r["date"], 0) + r["total"]
    return {"rows": rows, "ca": ca, "count": len(rows),
            "avg": ca / len(rows) if rows else 0,
            "by_cat": by_cat, "by_product": by_product, "by_date": by_date}

def compute_glovo_stats(start, end):
    db = get_db()
    rows = db.execute("SELECT * FROM sales_glovo WHERE date>=? AND date<=? ORDER BY date DESC, created_at DESC",
                       (start, end)).fetchall()
    compte = [r for r in rows if r["status"] != "annulee"]
    vraies_annulees = [r for r in rows if r["status"] == "annulee"]
    annulees_sorties = [r for r in rows if r["status"] == "annulee_sortie"]
    brut = sum(r["brut"] for r in compte)
    commission = sum(r["commission"] for r in compte)
    net = sum(r["net"] for r in compte)
    by_cat, by_product, by_date = {}, {}, {}
    for r in compte:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + r["net"]
        by_product[r["product_name"]] = by_product.get(r["product_name"], 0) + r["net"]
        by_date[r["date"]] = by_date.get(r["date"], 0) + r["net"]
    return {
        "rows": rows, "brut": brut, "commission": commission, "net": net,
        "count_livree": len([r for r in rows if r["status"] == "livree"]),
        "count_annulee_sortie": len(annulees_sorties),
        "montant_annulee_sortie": sum(r["net"] for r in annulees_sorties),
        "count_annulee": len(vraies_annulees),
        "taux_annulation": (len(vraies_annulees) / len(rows) * 100) if rows else 0,
        "by_cat": by_cat, "by_product": by_product, "by_date": by_date
    }

def compute_charges_stats(start, end):
    db = get_db()
    rows = db.execute("SELECT * FROM charges WHERE date>=? AND date<=? ORDER BY date DESC, created_at DESC",
                       (start, end)).fetchall()
    total = sum(r["amount"] for r in rows)
    by_cat, by_date = {}, {}
    for r in rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + r["amount"]
        by_date[r["date"]] = by_date.get(r["date"], 0) + r["amount"]
    return {"rows": rows, "total": total, "by_cat": by_cat, "by_date": by_date}

def get_products():
    db = get_db()
    rows = db.execute("SELECT * FROM products ORDER BY category, name").fetchall()
    return rows

def period_ctx():
    preset, start, end = period_range()
    return {"preset": preset, "start": start, "end": end,
            "label_start": fr_date(start), "label_end": fr_date(end)}

# ---------------------------------------------------------------- routes
@app.route("/")
def index():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    preset, start, end = period_range()
    m = compute_magasin_stats(start, end)
    gl = compute_glovo_stats(start, end)
    ch = compute_charges_stats(start, end)
    ca_total = m["ca"] + gl["net"]
    benefice = ca_total - ch["total"]
    days = date_series(start, end)

    combined_prod = {}
    for k, v in m["by_product"].items(): combined_prod[k] = combined_prod.get(k, 0) + v
    for k, v in gl["by_product"].items(): combined_prod[k] = combined_prod.get(k, 0) + v
    top_prod = top_n(combined_prod, 8)

    cat_set = sorted(set(list(m["by_cat"].keys()) + list(gl["by_cat"].keys())))
    cat_rows = [(c, m["by_cat"].get(c, 0), gl["by_cat"].get(c, 0)) for c in cat_set]
    cat_combined = {c: m["by_cat"].get(c, 0) + gl["by_cat"].get(c, 0) for c in cat_set}

    chart_data = {
        "days": [fr_date(d)[:5] for d in days],
        "mag_series": [round(m["by_date"].get(d, 0), 3) for d in days],
        "glo_series": [round(gl["by_date"].get(d, 0), 3) for d in days],
        "split": [round(m["ca"], 3), round(gl["net"], 3)],
        "top_prod_labels": [t[0] for t in top_prod],
        "top_prod_values": [round(t[1], 3) for t in top_prod],
        "cat_labels": list(cat_combined.keys()),
        "cat_values": [round(v, 3) for v in cat_combined.values()],
        "cat_colors": [CAT_COLORS.get(c, "#999") for c in cat_combined.keys()],
    }
    return render_template("dashboard.html", period=period_ctx(), m=m, gl=gl, ch=ch,
                            ca_total=ca_total, benefice=benefice, dt=dt,
                            cat_rows=cat_rows, chart_data=chart_data)

# ---------- Magasin ----------
@app.route("/magasin", methods=["GET", "POST"])
def magasin():
    if request.method == "POST":
        pid = request.form.get("product_id")
        date_ = request.form.get("date") or today_iso()
        qty = float(request.form.get("qty") or 0)
        unit_price = float(request.form.get("unit_price") or 0)
        db = get_db()
        prod = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if not prod or qty <= 0:
            flash("Vérifie le produit / la quantité.", "error")
        else:
            total = round(qty * unit_price, 3)
            db.execute("""INSERT INTO sales_store(id,date,product_id,product_name,category,unit,qty,unit_price,total,created_at)
                          VALUES (?,?,?,?,?,?,?,?,?,?)""",
                       (str(uuid.uuid4()), date_, prod["id"], prod["name"], prod["category"],
                        prod["unit"], qty, unit_price, total, datetime.now().isoformat()))
            db.commit()
            flash("Vente enregistrée ✓", "ok")
        return redirect(url_for("magasin", **request.args))

    preset, start, end = period_range()
    m = compute_magasin_stats(start, end)
    days = date_series(start, end)
    star = top_n(m["by_product"], 1)
    chart_data = {
        "days": [fr_date(d)[:5] for d in days],
        "series": [round(m["by_date"].get(d, 0), 3) for d in days],
        "cat_labels": list(m["by_cat"].keys()),
        "cat_values": [round(v, 3) for v in m["by_cat"].values()],
        "cat_colors": [CAT_COLORS.get(c, "#999") for c in m["by_cat"].keys()],
    }
    return render_template("magasin.html", period=period_ctx(), m=m, dt=dt,
                            products=get_products(), star=star[0] if star else None,
                            chart_data=chart_data, today=today_iso())

@app.route("/magasin/delete/<id>", methods=["POST"])
def magasin_delete(id):
    db = get_db()
    db.execute("DELETE FROM sales_store WHERE id=?", (id,))
    db.commit()
    flash("Vente supprimée", "ok")
    return redirect(url_for("magasin", **request.args))

# ---------- Glovo ----------
@app.route("/glovo", methods=["GET", "POST"])
def glovo():
    if request.method == "POST":
        pid = request.form.get("product_id")
        date_ = request.form.get("date") or today_iso()
        qty = float(request.form.get("qty") or 0)
        glovo_price = float(request.form.get("glovo_price") or 0)
        status = request.form.get("status") or "livree"
        db = get_db()
        prod = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if not prod or qty <= 0:
            flash("Vérifie le produit / la quantité.", "error")
        else:
            brut = round(qty * glovo_price, 3)
            commission = round(brut * GLOVO_COMMISSION, 3)
            net = round(brut - commission, 3)
            db.execute("""INSERT INTO sales_glovo(id,date,product_id,product_name,category,unit,qty,
                          store_price,glovo_price,brut,commission,net,status,created_at)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (str(uuid.uuid4()), date_, prod["id"], prod["name"], prod["category"], prod["unit"],
                        qty, prod["price"], glovo_price, brut, commission, net, status, datetime.now().isoformat()))
            db.commit()
            flash("Commande Glovo enregistrée ✓", "ok")
        return redirect(url_for("glovo", **request.args))

    preset, start, end = period_range()
    gl = compute_glovo_stats(start, end)
    days = date_series(start, end)
    chart_data = {
        "days": [fr_date(d)[:5] for d in days],
        "series": [round(gl["by_date"].get(d, 0), 3) for d in days],
        "status_values": [gl["count_livree"], gl["count_annulee_sortie"], gl["count_annulee"]],
    }
    return render_template("glovo.html", period=period_ctx(), gl=gl, dt=dt,
                            products=get_products(), chart_data=chart_data,
                            today=today_iso(), markup=GLOVO_MARKUP, commission_rate=GLOVO_COMMISSION)

@app.route("/glovo/delete/<id>", methods=["POST"])
def glovo_delete(id):
    db = get_db()
    db.execute("DELETE FROM sales_glovo WHERE id=?", (id,))
    db.commit()
    flash("Commande supprimée", "ok")
    return redirect(url_for("glovo", **request.args))

# ---------- Charges ----------
@app.route("/charges", methods=["GET", "POST"])
def charges():
    if request.method == "POST":
        date_ = request.form.get("date") or today_iso()
        category = request.form.get("category")
        description = request.form.get("description", "").strip()
        amount = float(request.form.get("amount") or 0)
        if amount <= 0:
            flash("Vérifie le montant.", "error")
        else:
            db = get_db()
            db.execute("""INSERT INTO charges(id,date,category,description,amount,created_at)
                          VALUES (?,?,?,?,?,?)""",
                       (str(uuid.uuid4()), date_, category, description, amount, datetime.now().isoformat()))
            db.commit()
            flash("Charge enregistrée ✓", "ok")
        return redirect(url_for("charges", **request.args))

    preset, start, end = period_range()
    ch = compute_charges_stats(start, end)
    days = date_series(start, end)
    top_cat = top_n(ch["by_cat"], 1)
    chart_data = {
        "days": [fr_date(d)[:5] for d in days],
        "series": [round(ch["by_date"].get(d, 0), 3) for d in days],
        "cat_labels": list(ch["by_cat"].keys()),
        "cat_values": [round(v, 3) for v in ch["by_cat"].values()],
    }
    return render_template("charges.html", period=period_ctx(), ch=ch, dt=dt,
                            charge_cats=CHARGE_CATS, top_cat=top_cat[0] if top_cat else None,
                            chart_data=chart_data, today=today_iso())

@app.route("/charges/delete/<id>", methods=["POST"])
def charges_delete(id):
    db = get_db()
    db.execute("DELETE FROM charges WHERE id=?", (id,))
    db.commit()
    flash("Charge supprimée", "ok")
    return redirect(url_for("charges", **request.args))

# ---------- Produits ----------
@app.route("/produits", methods=["GET", "POST"])
def produits():
    if request.method == "POST":
        category = request.form.get("category")
        name = request.form.get("name", "").strip()
        price = float(request.form.get("price") or 0)
        unit = request.form.get("unit")
        edit_id = request.form.get("edit_id")
        db = get_db()
        if not name:
            flash("Le nom du produit est requis.", "error")
        elif edit_id:
            db.execute("UPDATE products SET category=?, name=?, price=?, unit=? WHERE id=?",
                       (category, name, price, unit, edit_id))
            db.commit()
            flash("Produit modifié ✓", "ok")
        else:
            db.execute("INSERT INTO products(id,category,name,price,unit) VALUES (?,?,?,?,?)",
                       (str(uuid.uuid4()), category, name, price, unit))
            db.commit()
            flash("Produit ajouté ✓", "ok")
        return redirect(url_for("produits"))

    edit_id = request.args.get("edit")
    db = get_db()
    editing = db.execute("SELECT * FROM products WHERE id=?", (edit_id,)).fetchone() if edit_id else None
    products = get_products()
    grouped = {c: [p for p in products if p["category"] == c] for c in CATS}
    return render_template("produits.html", grouped=grouped, cats=CATS, editing=editing)

@app.route("/produits/delete/<id>", methods=["POST"])
def produits_delete(id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (id,))
    db.commit()
    flash("Produit supprimé", "ok")
    return redirect(url_for("produits"))

# ---------- Export CSV ----------
@app.route("/export/<kind>.csv")
def export_csv(kind):
    preset, start, end = period_range()
    db = get_db()
    if kind == "magasin":
        rows = db.execute("SELECT date,product_name,category,qty,unit_price,total FROM sales_store WHERE date>=? AND date<=? ORDER BY date DESC", (start, end)).fetchall()
        headers = ["Date", "Produit", "Catégorie", "Quantité", "PrixUnitaire", "Total"]
    elif kind == "glovo":
        rows = db.execute("SELECT date,product_name,qty,glovo_price,brut,commission,net,status FROM sales_glovo WHERE date>=? AND date<=? ORDER BY date DESC", (start, end)).fetchall()
        headers = ["Date", "Produit", "Quantité", "PrixGlovo", "Brut", "Commission", "Net", "Statut"]
    elif kind == "charges":
        rows = db.execute("SELECT date,category,description,amount FROM charges WHERE date>=? AND date<=? ORDER BY date DESC", (start, end)).fetchall()
        headers = ["Date", "Catégorie", "Description", "Montant"]
    else:
        return "Type inconnu", 404

    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(headers)
    for r in rows:
        writer.writerow(list(r))
    resp = Response(buf.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = f"attachment; filename={kind}_{today_iso()}.csv"
    return resp

# ---------------------------------------------------------------- main
# init_db() s'exécute toujours au chargement du module (pas seulement en
# lancement direct) : nécessaire pour que gunicorn / un hébergeur crée
# bien les tables au démarrage.
init_db()

if __name__ == "__main__":
    # host="0.0.0.0" permet d'y accéder depuis ton iPhone sur le même Wi-Fi
    # via l'adresse IP locale de ce PC (ex: http://192.168.1.24:5000)
    app.run(host="0.0.0.0", port=5000, debug=True)
