from flask import Flask, render_template, request, redirect, url_for, flash
from supabase import create_client, Client
from openpyxl import Workbook
from openpyxl.styles import Font
import io
from flask import send_file
import os
import logging
from types import SimpleNamespace
from dotenv import load_dotenv
from utils import tratar

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Colunas que podem ser usadas para ordenação na listagem (evita passar
# valores arbitrários vindos da URL direto para a query do Supabase)
COLUNAS_ORDENACAO_PERMITIDAS = {'artista', 'album', 'preco', 'quantidade'}


def parse_preco(valor):
    """
    Converte um preço digitado pelo usuário (aceita tanto vírgula quanto ponto
    como separador decimal, e ponto como separador de milhar) para float.
    Exemplos aceitos: "10,50" | "10.50" | "1.234,56" | "1234.56" | "1234,5"
    """
    if valor is None:
        raise ValueError("Preço vazio.")

    s = str(valor).strip()
    if not s:
        raise ValueError("Preço vazio.")

    # remove "R$" e espaços, caso venha nesse formato
    s = s.replace('R$', '').strip()

    if ',' in s and '.' in s:
        # formato "1.234,56" -> ponto é milhar, vírgula é decimal
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        # formato "10,50" -> vírgula é decimal
        s = s.replace(',', '.')
    # se só tem ponto, já está no formato que float() entende

    return float(s)


def formatar_preco(valor):
    """Formata um float como string no padrão brasileiro: 1234.5 -> '1234,50'"""
    return f"{float(valor):.2f}".replace('.', ',')

def validar_e_processar_form(form, cd_id=None):
    """
    Valida e converte os dados vindos do formulário de CD.

    Retorna uma tupla (dados, erro):
    - dados: dict pronto para insert/update no Supabase (ou None se houve erro)
    - erro: mensagem de erro para exibir via flash (ou None se tudo ok)

    cd_id: quando informado (edição), exclui o próprio registro da checagem
    de duplicidade.
    """
    artista = tratar(form['artista'])
    album = tratar(form['album'])
    descricao = tratar(form['descricao'])

    query = TABLE.table('albuns').select('*') \
        .ilike('artista', artista) \
        .ilike('album', album) \
        .ilike('descricao', descricao)
    if cd_id is not None:
        query = query.neq('id', cd_id)

    if query.execute().data:
        return None, 'Já existe um registro com esse artista, álbum e descrição.'

    try:
        preco_convertido = parse_preco(form['preco'])
    except ValueError:
        return None, 'Preço inválido. Use um formato como 10,50 ou 10.50.'

    if preco_convertido <= 0:
        return None, 'O preço deve ser maior que zero.'

    try:
        quantidade_convertida = int(form['quantidade'])
    except ValueError:
        return None, 'Quantidade inválida.'

    if quantidade_convertida <= 0:
        return None, 'A quantidade deve ser maior que zero.'

    return {
        'artista': artista,
        'album': album,
        'descricao': descricao,
        'preco': preco_convertido,
        'quantidade': quantidade_convertida
    }, None


app = Flask(__name__)
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("SECRET_KEY precisa estar no .env")

if not supabase_url or not supabase_key:
    raise RuntimeError("SUPABASE_URL e SUPABASE_KEY precisam estar no .env")

supabase: Client = create_client(supabase_url, supabase_key)
TABLE = supabase.schema('cadastro_cds')


@app.route('/criar_tabelas')
def criar_tabelas():
    return 'Use o SQL Editor do Supabase para criar a tabela.'


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    busca = request.args.get('busca', '')
    sort = request.args.get('sort', 'id')
    if sort not in COLUNAS_ORDENACAO_PERMITIDAS:
        sort = 'id'
    direction = request.args.get('direction', 'desc')

    start = (page - 1) * per_page
    end = start + per_page - 1

    query = TABLE.table('albuns').select('*', count='exact')

    if busca:
        query = query.ilike('artista', f'%{busca}%')

    query = query.order(sort, desc=(direction == 'desc'))

    query = query.range(start, end)

    result = query.execute()

    total = result.count or 0
    items = result.data or []
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    # converte dict para objeto (template usa cd.artista)
    item_objects = [SimpleNamespace(**item) for item in items]

    class Pagination:
        def __init__(self):
            self.items = item_objects
            self.page = page
            self.pages = total_pages
            self.total = total
            self.has_prev = page > 1
            self.has_next = page < total_pages
            self.prev_num = page - 1
            self.next_num = page + 1
            self.per_page = per_page

        def __iter__(self):
            return iter(self.items)

        def iter_pages(self):
            for p in range(1, self.pages + 1):
                if p <= 3 or p > self.pages - 3 or abs(p - self.page) <= 1:
                    yield p
                elif p == 4 or p == self.pages - 3:
                    yield None

    cds = Pagination()

    return render_template('index.html', cds=cds, request=request, sort=sort, direction=direction, busca=busca)


@app.route('/add', methods=['GET', 'POST'])
def add_cd():
    if request.method == 'POST':
        dados, erro = validar_e_processar_form(request.form)

        if erro:
            flash(erro)
            return render_template('form.html', cd=None)

        try:
            TABLE.table('albuns').insert(dados).execute()
            return redirect(url_for('index'))
        except Exception:
            logger.exception('Erro ao adicionar CD')
            flash('Erro ao adicionar CD. Tente novamente.')

    return render_template('form.html', cd=None)


@app.route('/edit/<int:cd_id>', methods=['GET', 'POST'])
def edit_cd(cd_id):
    result = TABLE.table('albuns').select('*').eq('id', cd_id).execute()
    cd = SimpleNamespace(**result.data[0]) if result.data else None
    if not cd:
        return 'Not found', 404

    if request.method == 'POST':
        dados, erro = validar_e_processar_form(request.form, cd_id=cd_id)

        if erro:
            flash(erro)
            return render_template('form.html', cd=cd)

        try:
            TABLE.table('albuns').update(dados).eq('id', cd_id).execute()
            return redirect(url_for('index'))
        except Exception:
            logger.exception('Erro ao editar CD %s', cd_id)
            flash('Erro ao editar CD. Tente novamente.')

    # exibe o preço já no formato brasileiro (com vírgula) ao carregar o form
    if cd:
        cd.preco = formatar_preco(cd.preco)

    return render_template('form.html', cd=cd)


@app.route('/delete/<int:cd_id>', methods=['POST'])
def delete_cd(cd_id):
    try:
        TABLE.table('albuns').delete().eq('id', cd_id).execute()
    except Exception:
        logger.exception('Erro ao excluir CD %s', cd_id)
        flash('Erro ao excluir CD. Tente novamente.')
    return redirect(url_for('index'))


@app.route('/exportar_produtos_xlsx')
def exportar_produtos_xlsx():
    result = TABLE.table('albuns').select('*').execute()
    items = result.data or []
    wb = Workbook()
    ws = wb.active
    ws.title = "CDs"
    ws.append(['Artista', 'Album', 'Descrição', 'Preço', 'Quantidade'])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for i in items:
        preco_formatado = f"R$ {(i.get('preco') or 0):,.2f}".replace('.', ',')
        ws.append([
            i.get('artista', ''),
            i.get('album', ''),
            i.get('descricao', ''),
            preco_formatado,
            i.get('quantidade', 0)
        ])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="registros.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)
