from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "chave_secreta_juazeiro"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///frota2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# BLOQUEIO GLOBAL DE SEGURANÇA (EXIGE LOGIN)
@app.before_request
def exigir_login():
    rotas_livres = ['login', 'static']
    # Liberamos também rotas que comecem com '/posto' caso queira acessar rotas internas do posto livremente se logado
    if request.endpoint and request.endpoint not in rotas_livres and 'usuario_admin' not in session and 'usuario_posto' not in session:
        return redirect(url_for('login'))


# CONFIGURAÇÕES DE UPLOAD
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def formata_real(v):
    """Função auxiliar padrão para formatar valores no padrão monetário brasileiro (R$ X.XXX,XX)"""
    try:
        val = float(v or 0.0)
    except (ValueError, TypeError):
        val = 0.0
    return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# ==============================================================================
# MODELOS DE DADOS
# ==============================================================================

class Veiculo(db.Model):
    __tablename__ = 'veiculos'
    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(100), nullable=False)
    placa = db.Column(db.String(20), nullable=False, unique=True)
    secretaria = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), default='Ativo')
    quilometragem = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'{self.modelo} ({self.placa})'


class SaldoSecretaria(db.Model):
    __tablename__ = 'saldos_secretarias'
    id = db.Column(db.Integer, primary_key=True)
    nome_secretaria = db.Column(db.String(100), nullable=False, unique=True)
    saldo_disponivel = db.Column(db.Float, nullable=False)


class Abastecimento(db.Model):
    __tablename__ = 'abastecimentos'
    id = db.Column(db.Integer, primary_key=True)
    veiculo = db.Column(db.String(100), nullable=False)
    secretaria = db.Column(db.String(100), nullable=False)
    motorista = db.Column(db.String(100), nullable=False)
    combustivel = db.Column(db.String(50), nullable=False)
    litros = db.Column(db.Float, nullable=False)
    km_atual = db.Column(db.Integer, nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    data = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.String(30), default='Concluído')

    @property
    def valor_total_formatado(self):
        return formata_real(self.valor_total)


class OrdemServico(db.Model):
    __tablename__ = 'ordens_servico'
    id = db.Column(db.Integer, primary_key=True)
    veiculo = db.Column(db.String(100), nullable=False)
    secretaria = db.Column(db.String(100), nullable=False, default="Prefeitura")
    oficina = db.Column(db.String(100), nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    tipo_servico = db.Column(db.String(50), nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default='Em Andamento')
    data = db.Column(db.DateTime, nullable=False, default=datetime.now)
    nota_fiscal = db.Column(db.String(150), nullable=True)

    @property
    def valor_formatado(self):
        return formata_real(self.valor)


class Motorista(db.Model):
    __tablename__ = 'motoristas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(20), nullable=False, unique=True)
    cnh = db.Column(db.String(10), nullable=False)


class Oficina(db.Model):
    __tablename__ = 'oficinas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    cnpj = db.Column(db.String(25), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)


class ConfigPreco(db.Model):
    __tablename__ = 'config_precos'
    id = db.Column(db.Integer, primary_key=True)
    combustivel = db.Column(db.String(50), unique=True, nullable=False)
    preco_litro = db.Column(db.Float, nullable=False)

    @property
    def preco_formatado(self):
        return formata_real(self.preco_litro)


# ==============================================================================
# SEED / CARGA INICIAL AUTOMÁTICA
# ==============================================================================
def inicializar_sistema():
    """Popula a frota municipal, motoristas, tabelas de preços, oficinas e saldos iniciais."""
    try:
        db.session.execute(
            db.text("UPDATE abastecimentos SET secretaria = 'Prefeitura' WHERE secretaria = 'Administração'"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    frota_completa = [
        {"modelo": "FORD F13.000", "placa": "JUA-0001", "secretaria": "Prefeitura"},
        {"modelo": "HYUNDAI HR", "placa": "JUA-0002", "secretaria": "Prefeitura"},
        {"modelo": "MERCEDES-BENZ L1313", "placa": "LVP-8772", "secretaria": "Prefeitura"},
        {"modelo": "ATRON 2729 K 6X4 2013", "placa": "LWE-8221", "secretaria": "Prefeitura"},
        {"modelo": "HILUX CD4X4 SRV 2011", "placa": "ODV-7D20", "secretaria": "Prefeitura"},
        {"modelo": "IVECO - TECTOR 260E28 2012", "placa": "OUB-2677", "secretaria": "Prefeitura"},
        {"modelo": "NEWHOLLAND WL W130 2014", "placa": "OVY-7383", "secretaria": "Prefeitura"},
        {"modelo": "MERCEDES-BENZ 415CDISPRINTERM 2017", "placa": "PIY-1530", "secretaria": "Prefeitura"},
        {"modelo": "FIAT DOBLO ESSENCE 2019", "placa": "QWX-7H39", "secretaria": "Prefeitura"},
        {"modelo": "TOYOTA HILUX CDLOWM4FD 2021", "placa": "RMX-1C56", "secretaria": "Prefeitura"},
        {"modelo": "RENAULT KWID ZEN 2 2022", "placa": "RSN-0C97", "secretaria": "Prefeitura"},
        {"modelo": "TRATOR AGRICOLA BUDNY 2020", "placa": "TAD-7540", "secretaria": "Prefeitura"},
        {"modelo": "TRATOR AGRICOLA MAHINDRA 2021", "placa": "TAD-7541", "secretaria": "Prefeitura"},
        {"modelo": "TRATOR AGRICOLA YANMAR 2024", "placa": "TAD-7542", "secretaria": "Prefeitura"},
        {"modelo": "MOTONIVELADORA CATERPILLAR 120K 2013", "placa": "TAD-7543", "secretaria": "Prefeitura"},
        {"modelo": "RETROESCAVADEIRA JCB 3C 2013", "placa": "TAD-7544", "secretaria": "Prefeitura"},
        {"modelo": "VOLKSWAGEN 15.190 EOD E.HD ORE 2011", "placa": "NIX-9058", "secretaria": "Educação"},
        {"modelo": "IVECO - FIAT CITYCLASS 70C16", "placa": "OEG-1587", "secretaria": "Educação"},
        {"modelo": "MEREDES-BENZ OF 1519 R.ORE 2013", "placa": "OUB-9759", "secretaria": "Educação"},
        {"modelo": "VOLKSWAGEN 15.190 OED E.S.ORE 2012", "placa": "PIB-0982", "secretaria": "Educação"},
        {"modelo": "MERCEDES-BENZ OF 1519 R.ORE", "placa": "PIF-1099", "secretaria": "Educação"},
        {"modelo": "TOYOTA HILUX CD4X4 STD 2015", "placa": "PIO-4290", "secretaria": "Educação"},
        {"modelo": "FIAT TORO ENDURANCE AT9 4X4 2022", "placa": "RPH-3A82", "secretaria": "Educação"},
        {"modelo": "VOLARE NEOBUS MINI ESC", "placa": "RSG-8D24", "secretaria": "Educação"},
        {"modelo": "IVECO BUS 15-210E-C 2024", "placa": "RSJ-6F78", "secretaria": "Educação"},
        {"modelo": "CITROEN AIRCROSS STARTMT 2020", "placa": "QRS-0E33", "secretaria": "Assistência Social"},
        {"modelo": "VOLKSWAGEN GOL 1.0 MC4 2021", "placa": "PIQ-7E47", "secretaria": "Assistência Social"},
        {"modelo": "TOYOTA HILUX CDSRVA4FD 2023", "placa": "SLT-6F48", "secretaria": "Assistência Social"},
        {"modelo": "RENAULT MASTER L2 CONC P 2023", "placa": "SUM-9C87", "secretaria": "Assistência Social"},
        {"modelo": "FIAT DUCATO ENGSS TP 2026", "placa": "UIY-1B45", "secretaria": "Assistência Social"},
        {"modelo": "FIAT UNO MILLE WAY ECON 2011", "placa": "NIS-4717", "secretaria": "Saúde"},
        {"modelo": "VOLKSWAGEM AMAROK AUTOMAR AMB", "placa": "OEG-8901", "secretaria": "Saúde"},
        {"modelo": "HILUX CD4X4 STD 2015", "placa": "PIK4-4H82", "secretaria": "Saúde"},
        {"modelo": "VOLKSWAGEN GOL 1.0L MC5 2018", "placa": "PIW-1237", "secretaria": "Saúde"},
        {"modelo": "VOLKSWAGEN GOL 1.0 MC5 2018", "placa": "PIW-1267", "secretaria": "Saúde"},
        {"modelo": "HONDA NXR BROS 160 2018", "placa": "PIW-4035", "secretaria": "Saúde"},
        {"modelo": "FIAT FIORINO MODIFICAR AB1 2018", "placa": "QRP-2581", "secretaria": "Saúde"},
        {"modelo": "RENAULT MASTER MARIM PASS 2019", "placa": "QRQ-8D86", "secretaria": "Saúde"},
        {"modelo": "RENAULT MASTER REVES A 2022", "placa": "SLM-0B90", "secretaria": "Saúde"},
        {"modelo": "FIAT STRADA FREEDOM CD13 2023", "placa": "SLR-0D56", "secretaria": "Saúde"}
    ]
    for v in frota_completa:
        placa_limpa = v["placa"].strip().upper()
        if not db.session.scalar(db.select(Veiculo).filter_by(placa=placa_limpa)):
            db.session.add(Veiculo(modelo=v["modelo"].strip().upper(), placa=placa_limpa, secretaria=v["secretaria"]))

    tabela_precos = {'Diesel S10': 7.80, 'Diesel Comum': 7.80, 'Gasolina Comum': 7.50}
    for comb, preco in tabela_precos.items():
        if not db.session.scalar(db.select(ConfigPreco).filter_by(combustivel=comb)):
            db.session.add(ConfigPreco(combustivel=comb, preco_litro=preco))

    secretarias = ["Prefeitura", "Educação", "Assistência Social", "Saúde"]
    for sec in secretarias:
        if not db.session.scalar(db.select(SaldoSecretaria).filter_by(nome_secretaria=sec)):
            db.session.add(SaldoSecretaria(nome_secretaria=sec, saldo_disponivel=360000.00))

    if not db.session.scalar(db.select(Motorista).filter_by(cpf="098.211.623-39")):
        db.session.add(Motorista(nome="Samuel Galvão", cpf="098.211.623-39", cnh="A/B"))

    if not db.session.scalar(db.select(Oficina).filter_by(nome="Erinaldo Auto Peças Pedro II")):
        db.session.add(
            Oficina(nome="Erinaldo Auto Peças Pedro II", cnpj="12.345.678/0001-90", telefone="(86) 99487-7688"))

    db.session.commit()


# ==============================================================================
# ROTAS GERAIS E ADMINISTRATIVAS
# ==============================================================================

@app.route('/')
def index():
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')

    query_abastecimentos = Abastecimento.query
    query_os = OrdemServico.query

    if data_inicio_str and data_fim_str:
        try:
            dt_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query_abastecimentos = query_abastecimentos.filter(Abastecimento.data >= dt_inicio,
                                                               Abastecimento.data <= dt_fim)
            query_os = query_os.filter(OrdemServico.data >= dt_inicio, OrdemServico.data <= dt_fim)
        except ValueError:
            pass

    abastecimentos = query_abastecimentos.order_by(Abastecimento.id.desc()).all()
    ordens_servico = query_os.order_by(OrdemServico.id.desc()).all()

    secretarias = ['Prefeitura', 'Saúde', 'Educação', 'Assistência Social']
    resumo_secretarias = {}

    for sec in secretarias:
        abast_sec = [a for a in abastecimentos if getattr(a, 'secretaria', '') == sec]
        soma_combustivel = sum([a.valor_total for a in abast_sec if a and a.valor_total])
        qtd_abast = len(abast_sec)

        os_sec = [o for o in ordens_servico if getattr(o, 'secretaria', '') == sec]
        soma_os = sum([o.valor for o in os_sec if o and o.valor])
        qtd_os = len(os_sec)

        resumo_secretarias[sec] = {
            'combustivel': f"R$ {soma_combustivel:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'qtd_abast': qtd_abast,
            'valor_os': f"R$ {soma_os:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'os_ativas': qtd_os
        }

    return render_template('index.html',
                           abastecimentos=abastecimentos,
                           ordens_servico=ordens_servico,
                           resumo_secretarias=resumo_secretarias,
                           data_inicio=data_inicio_str,
                           data_fim=data_fim_str,
                           tema=session.get('tema', 'light'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        # Login Administrativo
        if usuario == 'ricardo' and senha == '777':
            session['usuario_admin'] = 'admin'
            return redirect(url_for('index'))

        # Login do Posto unificado na mesma tela principal
        elif usuario == 'parente' and senha == '993304':
            session['usuario_posto'] = 'posto'
            return redirect(url_for('lancar_abastecimento'))

        flash('Credenciais incorretas.', 'danger')
    return render_template('login.html', tema=session.get('tema', 'claro'))


@app.route('/alternar_tema')
def alternar_tema():
    session['tema'] = 'dark' if session.get('tema') != 'dark' else 'light'
    return redirect(request.referrer or url_for('index'))

@app.route('/veiculos')
def veiculos():
    if 'usuario_admin' not in session: return redirect(url_for('login'))
    frota = db.session.scalars(db.select(Veiculo).order_by(Veiculo.secretaria.asc(), Veiculo.modelo.asc())).all()
    return render_template('veiculos.html', tema=session.get('tema', 'claro'), veiculos=frota)


@app.route('/motoristas')
def motoristas():
    if 'usuario_admin' not in session: return redirect(url_for('login'))
    lista = db.session.scalars(db.select(Motorista).order_by(Motorista.nome.asc())).all()
    return render_template('motoristas.html', tema=session.get('tema', 'claro'), motoristas=lista)


@app.route('/abastecimentos')
def abastecimentos():
    if 'usuario_admin' not in session: return redirect(url_for('login'))

    total_gasto = db.session.scalar(
        db.select(db.func.sum(Abastecimento.valor_total)).filter_by(status='Concluído')) or 0.0
    total_disponivel = db.session.scalar(db.select(db.func.sum(SaldoSecretaria.saldo_disponivel))) or 0.0
    historico = db.session.scalars(db.select(Abastecimento).order_by(Abastecimento.id.desc())).all()

    return render_template('abastecimentos.html',
                           tema=session.get('tema', 'claro'),
                           total_gasto=formata_real(total_gasto),
                           total_disponivel=formata_real(total_disponivel),
                           historico=historico)


@app.route('/os', methods=['GET', 'POST'])
def os_rota():
    if 'usuario_admin' not in session: return redirect(url_for('login'))

    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')

    if request.method == 'POST':
        string_veiculo = request.form.get('veiculo', '')
        oficina = request.form.get('oficina')
        tipo_servico = request.form.get('tipo_servico')
        valor_total = float(request.form.get('valor', 0.0))

        nome_arquivo_salvo = None
        if 'nota_fiscal' in request.files:
            file = request.files['nota_fiscal']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                nome_final = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_final))
                nome_arquivo_salvo = nome_final

        try:
            if '(' in string_veiculo and ')' in string_veiculo:
                placa_extraida = string_veiculo.split('(')[1].split(')')[0].strip().upper()
            else:
                placa_extraida = string_veiculo.strip().upper()

            veiculo_db = db.session.scalar(db.select(Veiculo).filter_by(placa=placa_extraida))
            secretaria_vinculada = veiculo_db.secretaria if veiculo_db else "Prefeitura"
        except Exception:
            secretaria_vinculada = "Prefeitura"

        nova_os = OrdemServico(
            veiculo=string_veiculo,
            secretaria=secretaria_vinculada,
            oficina=oficina,
            responsavel="Administração",
            tipo_servico=tipo_servico,
            valor=valor_total,
            nota_fiscal=nome_arquivo_salvo,
            data=datetime.now()
        )
        db.session.add(nova_os)
        db.session.commit()
        flash('Ordem de Serviço registrada com sucesso!', 'success')
        return redirect(url_for('os_rota'))

    veiculos_select = [f"{v.modelo} ({v.placa}) - {v.secretaria}" for v in
                       db.session.scalars(db.select(Veiculo).filter_by(status='Ativo')).all()]
    oficinas_select = [o.nome for o in db.session.scalars(db.select(Oficina).order_by(Oficina.nome.asc())).all()]

    query_os = OrdemServico.query
    if data_inicio_str and data_fim_str:
        try:
            dt_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query_os = query_os.filter(OrdemServico.data >= dt_inicio, OrdemServico.data <= dt_fim)
        except ValueError:
            pass

    historico_os = query_os.order_by(OrdemServico.id.desc()).all()

    return render_template('os.html',
                           veiculos=veiculos_select if veiculos_select else ['Nenhum veículo ativo'],
                           oficinas=oficinas_select if oficinas_select else ['Erinaldo Auto Peças Pedro II'],
                           historico=historico_os,
                           data_inicio=data_inicio_str,
                           data_fim=data_fim_str,
                           tema=session.get('tema', 'claro'))


@app.route('/os/concluir/<int:id>')
def concluir_os(id):
    if 'usuario_admin' not in session: return redirect(url_for('login'))
    ordem = db.session.get(OrdemServico, id)
    if not ordem: return redirect(url_for('os_rota'))
    ordem.status = 'Concluído'
    db.session.commit()
    return redirect(url_for('os_rota'))


@app.route('/os/cancelar/<int:id>')
def cancelar_os(id):
    if 'usuario_admin' not in session: return redirect(url_for('login'))
    ordem = db.session.get(OrdemServico, id)
    if not ordem: return redirect(url_for('os_rota'))
    ordem.status = 'Cancelado'
    db.session.commit()
    return redirect(url_for('os_rota'))


@app.route('/os/excluir/<int:id>')
def excluir_os(id):
    if 'usuario_admin' not in session: return redirect(url_for('login'))
    ordem = db.session.get(OrdemServico, id)
    if not ordem: return redirect(url_for('os_rota'))
    db.session.delete(ordem)
    db.session.commit()
    return redirect(url_for('os_rota'))


@app.route('/os/imprimir/<int:id>')
def imprimir_os(id):
    if 'usuario_admin' not in session: return redirect(url_for('login'))
    ordem = db.session.get(OrdemServico, id)
    if not ordem: return redirect(url_for('os_rota'))
    return render_template('imprimir_os.html', os=ordem, data_emissao=datetime.now().strftime('%d/%m/%Y %H:%M'))


# ==============================================================================
# CADASTROS ADICIONAIS: MOTORISTAS E OFICINAS/LOJAS
# ==============================================================================

@app.route('/motoristas/novo', methods=['POST'])
def cadastrar_motorista():
    if 'usuario_admin' not in session: return redirect(url_for('login'))

    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    cnh = request.form.get('cnh')

    if not nome or not cpf or not cnh:
        flash('Preencha todos os campos do motorista.', 'danger')
        return redirect(url_for('motoristas'))

    existente = db.session.scalar(db.select(Motorista).filter_by(cpf=cpf))
    if existente:
        flash('Este CPF já está cadastrado em nossa base!', 'warning')
        return redirect(url_for('motoristas'))

    novo_mot = Motorista(nome=nome, cpf=cpf, cnh=cnh)
    db.session.add(novo_mot)
    db.session.commit()
    flash('Motorista cadastrado com sucesso!', 'success')
    return redirect(url_for('motoristas'))


@app.route('/oficinas')
def oficinas():
    if 'usuario_admin' not in session: return redirect(url_for('login'))
    lista = db.session.scalars(db.select(Oficina).order_by(Oficina.nome.asc())).all()
    return render_template('oficinas.html', tema=session.get('tema', 'claro'), oficinas=lista)


@app.route('/oficinas/novo', methods=['POST'])
def cadastrar_oficina():
    if 'usuario_admin' not in session: return redirect(url_for('login'))

    nome = request.form.get('nome')
    cnpj = request.form.get('cnpj')
    telefone = request.form.get('telefone')

    if not nome:
        flash('O nome da Loja/Oficina é obrigatório!', 'danger')
        return redirect(url_for('oficinas'))

    existente = db.session.scalar(db.select(Oficina).filter_by(nome=nome))
    if existente:
        flash('Esta Loja/Oficina já está cadastrada!', 'warning')
        return redirect(url_for('oficinas'))

    nova_oficina = Oficina(nome=nome, cnpj=cnpj, telefone=telefone)
    db.session.add(nova_oficina)
    db.session.commit()
    flash('Loja/Oficina cadastrada com sucesso!', 'success')
    return redirect(url_for('oficinas'))


# ==============================================================================
# GESTÃO DE FATURAMENTO DE COMBUSTÍVEL (ISOLADO)
# ==============================================================================

@app.route('/faturamento')
@app.route('/faturamento/<secretaria>')
def faturamento(secretaria=None):
    if 'usuario_admin' not in session:
        return redirect(url_for('login'))

    secretarias_validas = ['Prefeitura', 'Saúde', 'Educação', 'Assistência Social']
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')

    if not secretaria or secretaria not in secretarias_validas:
        return render_template('faturamento.html',
                               secretaria=None,
                               secretarias=secretarias_validas,
                               data_inicio=data_inicio_str,
                               data_fim=data_fim_str,
                               tema=session.get('tema', 'claro'))

    query_abas = Abastecimento.query.filter(Abastecimento.secretaria == secretaria, Abastecimento.status != 'Estornado')

    if data_inicio_str and data_fim_str:
        try:
            dt_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query_abas = query_abas.filter(Abastecimento.data >= dt_inicio, Abastecimento.data <= dt_fim)
        except ValueError:
            pass

    abastecimentos_filtrados = query_abas.order_by(Abastecimento.id.desc()).all()
    total_comb = sum(float(abas.valor_total) for abas in abastecimentos_filtrados)

    return render_template('faturamento.html',
                           secretaria=secretaria,
                           abastecimentos=abastecimentos_filtrados,
                           total_combustivel=formata_real(total_comb),
                           total_faturado=formata_real(total_comb),
                           data_emissao=datetime.now().strftime('%d/%m/%Y'),
                           data_inicio=data_inicio_str,
                           data_fim=data_fim_str,
                           tema=session.get('tema', 'claro'))


@app.route('/faturamento/imprimir/<secretaria>')
def imprimir_faturamento(secretaria):
    if 'usuario_admin' not in session:
        return redirect(url_for('login'))

    secretarias_validas = ['Prefeitura', 'Saúde', 'Educação', 'Assistência Social']
    if secretaria not in secretarias_validas:
        return redirect(url_for('faturamento'))

    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')

    query_abas = Abastecimento.query.filter(Abastecimento.secretaria == secretaria, Abastecimento.status != 'Estornado')

    if data_inicio_str and data_fim_str:
        try:
            dt_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query_abas = query_abas.filter(Abastecimento.data >= dt_inicio, Abastecimento.data <= dt_fim)
        except ValueError:
            pass

    abastecimentos_filtrados = query_abas.order_by(Abastecimento.id.desc()).all()
    total_comb = sum(float(abas.valor_total) for abas in abastecimentos_filtrados)

    return render_template('imprimir_faturamento.html',
                           secretaria=secretaria,
                           abastecimentos=abastecimentos_filtrados,
                           total_combustivel=formata_real(total_comb),
                           total_faturado=formata_real(total_comb),
                           data_emissao=datetime.now().strftime('%d/%m/%Y'))


# ==============================================================================
# GESTÃO DE FATURAMENTO EXCLUSIVO DE ORDENS DE SERVIÇO (O.S.)
# ==============================================================================

@app.route('/faturamento_os')
@app.route('/faturamento_os/<secretaria>')
def faturamento_os(secretaria=None):
    if 'usuario_admin' not in session:
        return redirect(url_for('login'))

    secretarias_validas = ['Prefeitura', 'Saúde', 'Educação', 'Assistência Social']
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')

    if not secretaria or secretaria not in secretarias_validas:
        return render_template('faturamento_os.html',
                               secretaria=None,
                               secretarias=secretarias_validas,
                               data_inicio=data_inicio_str,
                               data_fim=data_fim_str,
                               tema=session.get('tema', 'claro'))

    query_os = OrdemServico.query.filter(OrdemServico.secretaria == secretaria)

    if data_inicio_str and data_fim_str:
        try:
            dt_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query_os = query_os.filter(OrdemServico.data >= dt_inicio, OrdemServico.data <= dt_fim)
        except ValueError:
            pass

    os_filtradas = query_os.order_by(OrdemServico.id.desc()).all()
    total_os_val = sum(float(os_item.valor) for os_item in os_filtradas)

    return render_template('faturamento_os.html',
                           secretaria=secretaria,
                           ordens_servico=os_filtradas,
                           total_faturado=formata_real(total_os_val),
                           data_emissao=datetime.now().strftime('%d/%m/%Y'),
                           data_inicio=data_inicio_str,
                           data_fim=data_fim_str,
                           tema=session.get('tema', 'claro'))


@app.route('/imprimir_faturamento_os/<secretaria>')
def imprimir_faturamento_os(secretaria):
    if 'usuario_admin' not in session:
        return redirect(url_for('login'))

    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')

    query_os = OrdemServico.query.filter(OrdemServico.secretaria == secretaria)

    if data_inicio_str and data_fim_str:
        try:
            dt_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            dt_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query_os = query_os.filter(OrdemServico.data >= dt_inicio, OrdemServico.data <= dt_fim)
        except ValueError:
            pass

    os_filtradas = query_os.order_by(OrdemServico.id.desc()).all()
    total_os_val = sum(float(os_item.valor) for os_item in os_filtradas)

    return render_template('imprimir_faturamento_os.html',
                           secretaria=secretaria,
                           ordens_servico=os_filtradas,
                           total_faturado=formata_real(total_os_val),
                           data_emissao=datetime.now().strftime('%d/%m/%Y'))


# ==============================================================================
# PORTAL DO POSTO CONVENIADO (OPERAÇÕES E ESTORNO)
# ==============================================================================

@app.route('/posto/abastecer', methods=['GET', 'POST'])
def lancar_abastecimento():
    if 'usuario_posto' not in session and 'usuario_admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        string_veiculo = request.form.get('veiculo', '')
        nome_motorista = request.form.get('motorista')
        valor_total = float(request.form.get('valor_total', 0.0))
        km_informado = int(request.form.get('km_atual', 0))

        try:
            if '(' in string_veiculo and ')' in string_veiculo:
                placa_extraida = string_veiculo.split('(')[1].split(')')[0].strip().upper()
            else:
                placa_extraida = string_veiculo.strip().upper()

            veiculo_db = db.session.scalar(db.select(Veiculo).filter_by(placa=placa_extraida))
            secretaria_vinculada = veiculo_db.secretaria if veiculo_db else "Prefeitura"
        except Exception:
            placa_extraida = None
            secretaria_vinculada = "Prefeitura"

        saldo_sec = db.session.scalar(db.select(SaldoSecretaria).filter_by(nome_secretaria=secretaria_vinculada))
        if saldo_sec and saldo_sec.saldo_disponivel < valor_total:
            flash(f'Margem Recusada! Saldo insuficiente na secretaria: {secretaria_vinculada}', 'danger')
            return redirect(url_for('lancar_abastecimento'))

        if saldo_sec:
            saldo_sec.saldo_disponivel -= valor_total

        novo = Abastecimento(
            veiculo=string_veiculo,
            secretaria=secretaria_vinculada,
            motorista=nome_motorista,
            combustivel=request.form.get('combustivel'),
            litros=float(request.form.get('litros', 0.0)),
            km_atual=km_informado,
            valor_total=valor_total,
            data=datetime.now()
        )
        db.session.add(novo)

        try:
            if placa_extraida and veiculo_db:
                if km_informado > (veiculo_db.quilometragem or 0):
                    veiculo_db.quilometragem = km_informado
        except Exception as e:
            print(f"Erro ao atualizar quilometragem do veículo: {e}")

        db.session.commit()
        flash('Cupom de Abastecimento emitido e gravado!', 'success')
        return redirect(url_for('lancar_abastecimento'))

    veic_list = [f"{v.modelo} ({v.placa}) - {v.secretaria}" for v in
                 db.session.scalars(db.select(Veiculo).filter_by(status='Ativo')).all()]

    return render_template('posto_abastecer.html', veiculos=veic_list)


@app.route('/posto/nota/<int:id>')
def nota_abastecimento(id):
    if 'usuario_posto' not in session and 'usuario_admin' not in session:
        return redirect(url_for('login_posto'))
    item = db.session.get(Abastecimento, id)
    if not item: return redirect(url_for('lancar_abastecimento'))
    return render_template('nota_abastecimento.html', item=item)


@app.route('/posto/estornar/<int:id>')
def estornar_abastecimento(id):
    if 'usuario_posto' not in session and 'usuario_admin' not in session:
        return redirect(url_for('login_posto'))
    item = db.session.get(Abastecimento, id)
    if not item or item.status == 'Estornado':
        return redirect(url_for('lancar_abastecimento'))

    item.status = 'Estornado'
    saldo_sec = db.session.scalar(db.select(SaldoSecretaria).filter_by(nome_secretaria=item.secretaria))
    if saldo_sec:
        saldo_sec.saldo_disponivel += item.valor_total

    db.session.commit()
    flash(f'Abastecimento #{item.id:04d} estornado com sucesso!', 'warning')
    return redirect(url_for('lancar_abastecimento'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        inicializar_sistema()
    app.run(debug=True, port=5000)