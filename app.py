from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from openpyxl import Workbook
from openpyxl.styles import Font
import io
from flask import send_file
import os
from utils import *

app = Flask(__name__)
database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {"sslmode": "require"}
}
db = SQLAlchemy(app)

class CD(db.Model):
    __tablename__ = 'cd'
    __table_args__ = {'schema': 'cadastro_cds'}
    
    id = db.Column(db.Integer, primary_key=True)
    artista = db.Column(db.String(100), nullable=False)
    album = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    preco = db.Column(db.Float, nullable=False)    
    quantidade = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('artista', 'album', 'descricao', name='unique_cd'),
        {'schema': 'cadastro_cds'}
    )


@app.route('/criar_tabelas')  
def criar_tabelas():  
    db.create_all()  
    return 'Tabelas criadas com sucesso!'

@app.route('/')  
def index():
    page = request.args.get('page', 1, type=int)  
    per_page = 10
    busca = request.args.get('busca', '')  
    sort = request.args.get('sort', 'id')  
    direction = request.args.get('direction', 'desc')  

    # Construir a query base
    query = CD.query  
    
    # Aplicar filtro de busca
    if busca:  
        query = query.filter(func.lower(CD.artista).contains(busca.lower()))  

    # Aplicar ordenação
    sort_column = getattr(CD, sort, CD.id)  
    if direction == 'desc':  
        sort_column = sort_column.desc()  
    else:  
        sort_column = sort_column.asc()  
    query = query.order_by(sort_column)  

    # ✅ USAR APENAS .paginate() - remove o resto
    cds = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('index.html', cds=cds, request=request, sort=sort, direction=direction, busca=busca)

@app.route('/add', methods=['GET', 'POST'])
def add_cd():
    if request.method == 'POST':
        artista = tratar(request.form['artista'])
        album = tratar(request.form['album'])
        descricao = tratar(request.form['descricao'])
        preco = request.form['preco']
        quantidade = request.form['quantidade']
        # Validação de unicidade (case insensitive)
        exists = CD.query.filter(CD.artista == artista, CD.album == album, CD.descricao == descricao).first()
        if exists:
            flash('Já existe um CD com esse artista, álbum e descrição.')
            return render_template('form.html', cd=None)
        try:
            cd = CD(artista=artista, album=album, descricao=descricao, preco=float(preco), quantidade=int(quantidade))
            db.session.add(cd)
            db.session.commit()

            # Formatar preço para a mensagem
            preco_formatado = f"R$ {float(preco):,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
            
            return redirect(url_for('index'))
        except Exception as e:
            flash('Erro ao adicionar CD: ' + str(e))
    return render_template('form.html', cd=None)

@app.route('/edit/<int:cd_id>', methods=['GET', 'POST'])
def edit_cd(cd_id):
    cd = CD.query.get_or_404(cd_id)
    if request.method == 'POST':
        artista = tratar(request.form['artista'])
        album = tratar(request.form['album'])
        descricao = tratar(request.form['descricao'])
        preco = request.form['preco']
        quantidade = request.form['quantidade']
        # Validação de unicidade (case insensitive), exceto o próprio registro
        exists = CD.query.filter(
            func.lower(CD.artista) == artista.lower(),
            func.lower(CD.album) == album.lower(),
            func.lower(CD.descricao) == descricao.lower(),
            CD.id != cd_id
        ).first()
        if exists:
            flash('Já existe um CD com esse artista, álbum e descrição.')
            return render_template('form.html', cd=cd)
        try:
            quantidade_anterior = cd.quantidade
            cd.artista = artista
            cd.album = album
            cd.descricao = descricao
            cd.preco = float(preco)
            cd.quantidade = int(quantidade)
            db.session.commit()

            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('Já existe um CD com esse artista, álbum e descrição.')
            return render_template('form.html', cd=cd)
        except Exception as e:
            flash('Erro ao editar CD: ' + str(e))
            return render_template('form.html', cd=cd)
    return render_template('form.html', cd=cd)

@app.route('/delete/<int:cd_id>')
def delete_cd(cd_id):
    cd = CD.query.get_or_404(cd_id)
    info = f"{cd.artista} - {cd.album} - {cd.descricao}"
    db.session.delete(cd)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/exportar_produtos_xlsx')
def exportar_produtos_xlsx():
    items = CD.query.all()    
    wb = Workbook()
    ws = wb.active
    ws.title = "CDS"
    ws.append(['Artista', 'Album', 'Descrição', 'Preço', 'Quantidade'])
    for cell in ws[1]:  
        cell.font = Font(bold=True) 
    for i in items:
        preco_formatado = f"R$ {i.preco:,.2f}".replace('.', ',')
        ws.append([i.artista, i.album, i.descricao, preco_formatado, i.quantidade])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)    
    return send_file(
        output,
        as_attachment=True,
        download_name="registros.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )



