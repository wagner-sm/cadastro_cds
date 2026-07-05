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

class albuns(db.Model):
    __tablename__ = 'albuns'
    __table_args__ = {'schema': 'cadastro_albuns'}
    
    id = db.Column(db.Integer, primary_key=True)
    artista = db.Column(db.String(100), nullable=False)
    album = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    preco = db.Column(db.Float, nullable=False)    
    quantidade = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('artista', 'album', 'descricao', name='unique_albuns'),
        {'schema': 'cadastro_albuns'}
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
    query = albuns.query  
    
    # Aplicar filtro de busca
    if busca:  
        query = query.filter(func.lower(albuns.artista).contains(busca.lower()))  

    # Aplicar ordenação
    sort_column = getattr(albuns, sort, albuns.id)  
    if direction == 'desc':  
        sort_column = sort_column.desc()  
    else:  
        sort_column = sort_column.asc()  
    query = query.order_by(sort_column)  

    # ✅ USAR APENAS .paginate() - remove o resto
    albunss = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('index.html', albunss=albunss, request=request, sort=sort, direction=direction, busca=busca)

@app.route('/add', methods=['GET', 'POST'])
def add_albuns():
    if request.method == 'POST':
        artista = tratar(request.form['artista'])
        album = tratar(request.form['album'])
        descricao = tratar(request.form['descricao'])
        preco = request.form['preco']
        quantidade = request.form['quantidade']
        # Validação de unicidade (case insensitive)
        exists = albuns.query.filter(albuns.artista == artista, albuns.album == album, albuns.descricao == descricao).first()
        if exists:
            flash('Já existe um registro com esse artista, álbum e descrição.')
            return render_template('form.html', albuns=None)
        try:
            albuns = albuns(artista=artista, album=album, descricao=descricao, preco=float(preco), quantidade=int(quantidade))
            db.session.add(albuns)
            db.session.commit()

            # Formatar preço para a mensagem
            preco_formatado = f"R$ {float(preco):,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
            
            return redirect(url_for('index'))
        except Exception as e:
            flash('Erro ao adicionar albuns: ' + str(e))
    return render_template('form.html', albuns=None)

@app.route('/edit/<int:albuns_id>', methods=['GET', 'POST'])
def edit_albuns(albuns_id):
    albuns = albuns.query.get_or_404(albuns_id)
    if request.method == 'POST':
        artista = tratar(request.form['artista'])
        album = tratar(request.form['album'])
        descricao = tratar(request.form['descricao'])
        preco = request.form['preco']
        quantidade = request.form['quantidade']
        # Validação de unicidade (case insensitive), exceto o próprio registro
        exists = albuns.query.filter(
            func.lower(albuns.artista) == artista.lower(),
            func.lower(albuns.album) == album.lower(),
            func.lower(albuns.descricao) == descricao.lower(),
            albuns.id != albuns_id
        ).first()
        if exists:
            flash('Já existe um registro com esse artista, álbum e descrição.')
            return render_template('form.html', albuns=albuns)
        try:
            quantidade_anterior = albuns.quantidade
            albuns.artista = artista
            albuns.album = album
            albuns.descricao = descricao
            albuns.preco = float(preco)
            albuns.quantidade = int(quantidade)
            db.session.commit()

            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('Já existe um registro com esse artista, álbum e descrição.')
            return render_template('form.html', albuns=albuns)
        except Exception as e:
            flash('Erro ao editar albuns: ' + str(e))
            return render_template('form.html', albuns=albuns)
    return render_template('form.html', albuns=albuns)

@app.route('/delete/<int:albuns_id>')
def delete_albuns(albuns_id):
    albuns = albuns.query.get_or_404(albuns_id)
    info = f"{albuns.artista} - {albuns.album} - {albuns.descricao}"
    db.session.delete(albuns)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/exportar_produtos_xlsx')
def exportar_produtos_xlsx():
    items = albuns.query.all()    
    wb = Workbook()
    ws = wb.active
    ws.title = "albunsS"
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
