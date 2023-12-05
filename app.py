from uuid import uuid4
from datetime import datetime, timedelta
import openpyxl
import os
from flask import Flask, render_template, request, url_for, redirect, Response, send_from_directory, send_file,session, flash
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import io
import xlsxwriter
from werkzeug.utils import secure_filename
from dateutil.relativedelta import relativedelta
from functools import wraps


if not os.path.exists('uploads'):
    os.makedirs('uploads')

app = Flask(__name__)


app.template_folder = 'templates'
app.config['BASE_URL'] = '/'  # Ruta base de la aplicación
app.config['UPLOAD_FOLDER'] = r'C:\Users\mastorga\Desktop\Seguimiento Equipos - Pleito\Sistema Gestión Documentación\upload'
# Lista de trabajadores (de ejemplo)
app.secret_key = '1234'

workers = []

registered_users = [
    {'username': 'usuario1', 'password': '1'},
    {'username': 'usuario2', 'password': 'contraseña2'},
    {'username': 'rvalenzuela', 'password': '123rovz'},
]    
@app.route('/', methods=['GET'])
def home():
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' not in session:
        session['logged_in'] = False
        return render_template('login.html')
    if request.method == 'POST':
        # Obtén los datos del formulario de inicio de sesión
        username = request.form['username']
        password = request.form['password']
        
        # Verifica si las credenciales coinciden con algún usuario registrado
        for user in registered_users:
            if user['username'] == username and user['password'] == password:
                session['logged_in'] = True
                session['username'] = username
                # Si las credenciales son correctas, redirige al usuario a la página principal
                return render_template('index.html')

        # Si las credenciales son incorrectas, muestra un mensaje de error
        error = "Credenciales incorrectas. Por favor, inténtalo de nuevo."
        # Renderiza la página de inicio de sesión con el mensaje de error
        return render_template('login.html', error=error)

    # Si el método es GET, simplemente renderiza la página de inicio de sesión
    # Aquí debes inicializar la sesión también para usuarios no autenticados
    
    return render_template('login.html')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Debes iniciar sesión primero.', 'warning')
            print("Usuario no autenticado. Redirigiendo a la página de inicio de sesión.")
            return redirect(url_for('login'))
        print("Usuario autenticado. Acceso permitido.")
        return f(*args, **kwargs)
    return decorated_function

template_dir = "templates"  # Asegúrate de que esto apunte al directorio donde tienes tus plantillas
loader = FileSystemLoader(template_dir)
env = Environment(loader=loader)
contract_types = ["Contrato Plazo Fijo", "Contrato Faena", "Contrato Indefinido"]

# Añade el entorno de Jinja2 a la aplicación Flask
env.filters['date'] = lambda value, format: value.strftime(format)
app.jinja_env = env 




@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    
    search_name = request.args.get('search_name')
    search_rut = request.args.get('search_rut')

    
    
    if search_name:
        filtered_workers = [worker for worker in workers if search_name.lower() in worker['name'].lower()]
        return render_template('index.html', workers=filtered_workers, base_url=app.config['BASE_URL'])
    if search_rut:
        filtered_workers = [worker for worker in workers if search_rut.lower() in worker['document'].lower()]
        return render_template('index.html', workers=filtered_workers, base_url=app.config['BASE_URL'])

    # Calcula las edades en lugar de los días faltantes
    today = datetime.now().date()
    
    for worker in workers:
        birth_date = datetime.strptime(worker['birth_date'], '%d-%m-%Y').date()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        worker['age'] = age
    
    return render_template('index.html', workers=workers, base_url=app.config['BASE_URL'])


@app.route('/add_worker', methods=['POST'])
@login_required
def add_worker():
   
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    name = request.form['name']
    document = request.form['document']
    position = request.form['position']
    birth_date = request.form['birth_date']
    worker_id = str(uuid4())  # Genera un ID único
    worker = {'id': worker_id, 'name': name, 'document': document, 'position': position, 'birth_date': birth_date}

    # Calcule la edad
    birth_date = datetime.strptime(birth_date, '%d-%m-%Y')
    today = datetime.now().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    worker['age'] = age

    workers.append(worker)
    return redirect(url_for('index'))

@app.route('/edit_worker/<string:id>', methods=['GET', 'POST'])
@login_required
def edit_worker(id):
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    worker = get_worker_by_id(id)
    if worker:
        if request.method == 'POST':
            # Verifica si se ha enviado un archivo
            if 'file' in request.files:
                file = request.files['file']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    worker['photo'] = filename

            # Actualiza los otros datos del trabajador
            new_name = request.form['name']
            new_document = request.form['document']
            new_position = request.form['position']
            new_birth_date = request.form['birth_date']
            # Actualiza los datos del trabajador, incluyendo la foto
            worker['name'] = new_name
            worker['document'] = new_document
            worker['position'] = new_position
            worker['birth_date'] = new_birth_date
            birth_date = datetime.strptime(new_birth_date, '%d-%m-%Y')
            today = datetime.now().date()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            worker['age'] = age

            return redirect(url_for('index'))


        return render_template('edit_worker.html', worker=worker, base_url=app.config['BASE_URL'])
    return "Trabajador no encontrado"

    

@app.route('/delete_worker/<string:id>')
@login_required
def delete_worker(id):
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    worker_to_delete = get_worker_by_id(id)
    if worker_to_delete:
        workers.remove(worker_to_delete)
    return redirect(url_for('index'))

def get_worker_by_id(id):
    for worker in workers:
        if worker['id'] == id:
            return worker
    return None

@app.route('/export_to_excel', methods=['GET'])
@login_required
def export_to_excel():

    if 'logged_in' not in session:
        # Si no ha iniciado sesión, redirige al usuario a la página de inicio de sesión
        flash('Debes iniciar sesión primero.', 'warning')  # Mensaje opcional para mostrar al usuario
        return redirect(url_for('login'))
    
    if len(workers) == 0:
        return "No hay trabajadores para exportar."

    df = pd.DataFrame(workers)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter', mode='xlsx') as writer:
        df.to_excel(writer, sheet_name='Trabajadores', index=False)

    output.seek(0)
    return Response(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")



def save_edited_worker(id):
    if request.method == 'POST':
        new_name = request.form['name']
        new_document = request.form['document']
        new_position = request.form['position']
        new_birth_date = request.form['birth_date']

        for worker in workers:
            if worker['id'] == id:
                worker['name'] = new_name
                worker['document'] = new_document
                worker['position'] = new_position
                worker['birth_date'] = new_birth_date
                # Actualiza la edad
                birth_date = datetime.strptime(new_birth_date, '%d-%m-%Y')
                today = datetime.now().date()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                worker['age'] = age

                return redirect(url_for('index'))

    return "Trabajador no encontrado", 404

@app.route('/import_mass_data', methods=['GET', 'POST'])
@login_required
def import_mass_data():
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        print(request.files)  # Agrega esta línea para ver qué archivos se están enviando

        if 'file' not in request.files or request.files['file'].filename == '':
            return "No se seleccionó ningún archivo."

        file = request.files['file']
        print(file)  # Agrega esta línea para ver detalles sobre el archivo

        if file.filename == '':
            return "Nombre de archivo vacío."
        try:
            workbook = openpyxl.load_workbook(file)
            worksheet = workbook.active

            imported_data = []

            for row in worksheet.iter_rows(values_only=True):
                name, document, position, formatted_birth_date, contract_commercial, contract_type, start_date, end_date, shift_type , id_or_passport_start_date, id_or_passport_end_date,	id_or_passport_tipo_alerta_dias, id_or_contrato_start_date,	id_or_contrato_end_date,	id_or_contrato_tipo_alerta_dias,	id_or_anexo_start_date,	id_or_anexo_end_date,	id_or_anexo_tipo_alerta_dias,	id_or_odi_start_date,	id_or_odi_end_date,	id_or_odi_tipo_alerta_dias,	id_or_ocupacional_start_date,	id_or_ocupacional_end_date,	id_or_ocupacional_tipo_alerta_dias, id_or_mun_start_date,	id_or_mun_end_date,	id_or_mun_tipo_alerta_dias,	id_or_psico_start_date,	id_or_psico_end_date,	id_or_psico_tipo_alerta_dias,	id_or_cmd_start_date,	id_or_cmd_end_date,	id_or_cmd_tipo_alerta_dias,	id_or_curso_start_date,	id_or_curso_end_date,	id_or_curso_tipo_alerta_dias, id_or_RIOHS_start_date, id_or_RIOHS_end_date, id_or_RIOHS_tipo_alerta_dias, id_or_EPP_start_date,	id_or_EPP_end_date,	id_or_EPP_tipo_alerta_dias,	id_or_Teck_start_date, id_or_Teck_end_date,	id_or_Teck_tipo_alerta_dias, id_or_ODI_CMP_start_date, id_or_ODI_CMP_end_date, id_or_ODI_CMP_tipo_alerta_dias = row
 

                if name and document and position and formatted_birth_date:
                    if isinstance(formatted_birth_date, datetime):
                        formatted_birth_date = formatted_birth_date.strftime('%d-%m-%Y')

                    worker_id = str(uuid4())  # Genera un ID único

                    # Crea un diccionario con la información del trabajador
                    worker_data = {
                        'id': worker_id,
                        'name': name,
                        'document': document,
                        'position': position,
                        'birth_date': formatted_birth_date,
                        'contract_commercial': contract_commercial,
                        'contract_type': contract_type,
                        'start_date': start_date,
                        'end_date': end_date,
                        'shift_type': shift_type,
                        'id_or_passport_start_date': id_or_passport_start_date,
                        'id_or_passport_end_date':	id_or_passport_end_date,
                        'id_or_passport_tipo_alerta_dias':	id_or_passport_tipo_alerta_dias,
                        'id_or_contrato_start_date':	id_or_contrato_start_date,
                        'id_or_contrato_end_date':	id_or_contrato_end_date,
                        'id_or_contrato_tipo_alerta_dias':	id_or_contrato_tipo_alerta_dias,
                        'id_or_anexo_start_date':	id_or_anexo_start_date,
                        'id_or_anexo_end_date':	id_or_anexo_end_date,
                        'id_or_anexo_tipo_alerta_dias':	id_or_anexo_tipo_alerta_dias,
                        'id_or_odi_start_date':	id_or_odi_start_date,
                        'id_or_odi_end_date':	id_or_odi_end_date,
                        'id_or_odi_tipo_alerta_dias': id_or_odi_tipo_alerta_dias,
                        'id_or_ocupacional_start_date':	id_or_ocupacional_start_date,
                        'id_or_ocupacional_end_date':	id_or_ocupacional_end_date,
                        'id_or_ocupacional_tipo_alerta_dias':	id_or_ocupacional_tipo_alerta_dias,
                        'id_or_mun_start_date':	id_or_mun_start_date,
                        'id_or_mun_end_date':	id_or_mun_end_date,
                        'id_or_mun_tipo_alerta_dias':	id_or_mun_tipo_alerta_dias,
                        'id_or_psico_start_date':	id_or_psico_start_date,
                        'id_or_psico_end_date':	id_or_psico_end_date,
                        'id_or_psico_tipo_alerta_dias':	id_or_psico_tipo_alerta_dias,
                        'id_or_cmd_start_date':	id_or_cmd_start_date,
                        'id_or_cmd_end_date':	id_or_cmd_end_date,
                        'id_or_cmd_tipo_alerta_dias':	id_or_cmd_tipo_alerta_dias,
                        'id_or_curso_start_date':	id_or_curso_start_date,
                        'id_or_curso_end_date':	id_or_curso_end_date,
                        'id_or_curso_tipo_alerta_dias':	id_or_curso_tipo_alerta_dias,
                        'id_or_RIOHS_start_date': id_or_RIOHS_start_date,
                        'id_or_RIOHS_end_date': id_or_RIOHS_end_date,
                        'id_or_RIOHS_tipo_alerta_dias': id_or_RIOHS_tipo_alerta_dias,
                        'id_or_EPP_start_date': id_or_EPP_start_date,
                        'id_or_EPP_end_date': id_or_EPP_end_date,
                        'id_or_EPP_tipo_alerta_dias': id_or_EPP_tipo_alerta_dias,
                        'id_or_Teck_start_date': id_or_Teck_start_date,
                        'id_or_Teck_end_date': id_or_Teck_end_date,
                        'id_or_Teck_tipo_alerta_dias': id_or_Teck_tipo_alerta_dias,
                        'id_or_ODI_CMP_start_date': id_or_ODI_CMP_start_date, 
                        'id_or_ODI_CMP_end_date': id_or_ODI_CMP_end_date,
                        'id_or_ODI_CMP_tipo_alerta_dias': id_or_ODI_CMP_tipo_alerta_dias,


                    }

                    # Agrega datos adicionales al diccionario
                    add_contract_info(worker_data)

                    
                    imported_data.append(worker_data)

            # Extiende la lista de trabajadores con los nuevos datos
            workers.extend(imported_data)

            # Recalcula la edad para los trabajadores importados
            today = datetime.now().date()
            for worker in imported_data:
                birth_date = datetime.strptime(worker['birth_date'], '%d-%m-%Y').date()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                worker['age'] = age

            # Redirige al usuario a la página de inicio después de la importación exitosa
            return redirect(url_for('index'))
            

        except Exception as e:
            return f"Error en la importación: {str(e)}"

    return render_template('import_mass_data.html')  # Renderiza la plantilla import_mass_data_html si es un GET

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.isfile(file_path):
        response = send_file(file_path, mimetype='application/pdf', as_attachment=True)
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    else:
        return "Archivo no encontrado", 404
    
    
contract_types = ["Contrato Plazo Fijo", "Contrato Faena", "Contrato Indefinido"]



@app.route('/view_worker/<string:id>', methods=['GET', 'POST'])
def view_worker(id):
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    worker = get_worker_by_id(id)
    edit_mode = False
    
    if worker:
        if request.method == 'POST':
            # Maneja la información contractual
            contract_commercial = request.form.get('contract_commercial')
            contract_type = request.form.get('contract_type')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            shift_type = request.form.get('shift_type')

            # Actualiza la información contractual en el trabajador
            worker['contract_commercial'] = contract_commercial
            worker['contract_type'] = contract_type
            worker['start_date'] = start_date if start_date else None  # Garantiza que la fecha no esté vacía
            worker['end_date'] = end_date
            worker['shift_type'] = shift_type

            edit_mode = True  # Actualiza edit_mode a True

        if 'contract_commercial' not in worker:
            worker['contract_commercial'] = ''
        if 'contract_type' not in worker:
            worker['contract_type'] = ''
        if 'start_date' not in worker:
            worker['start_date'] = ''
        if 'end_date' not in worker:
            worker['end_date'] = ''
        if 'shift_type' not in worker:
            worker['shift_type'] = ''

        # Asegura que la fecha de inicio del contrato no esté vacía antes de realizar el cálculo
        if worker['start_date']:
            # Calcula la antigüedad laboral en años y meses
            if isinstance(worker['start_date'], datetime):
                job_start_date = worker['start_date'].date()
            else:
                job_start_date = datetime.strptime(worker['start_date'], '%Y-%m-%d').date()
            today = datetime.now().date()
            job_experience = relativedelta(today, job_start_date)
            worker['job_experience'] = job_experience

        documentos = [
            ('id_or_passport', 'Cedula de Identidad o Pasaporte'),
            ('id_or_contrato', 'Contrato de Trabajo'),
            ('id_or_anexo', 'Anexo de Trabajo'),
            ('id_or_odi', 'Obligación de Informar'),
            ('id_or_ocupacional', 'Exámenes de Salud'),
            ('id_or_mun', 'Licencia Municipal'),
            ('id_or_psico', 'Cert. Examen Psico-Sensométrico'),
            ('id_or_cmd', 'Curso Manejo a la Defensiva'),
            ('id_or_curso', 'Certificado o Curso Especifico por Cargo'),
            ('id_or_RIOHS', 'Comprobante entrega RIOHS'),
            ('id_or_EPP', 'Comprobante entrega EPP'),
            ('id_or_Teck', 'Inducción Teck'),
            ('id_or_ODI_CMP', 'Obligación de Informar CMP'),
        ]

        # Renderiza la plantilla view_worker.html con la información del trabajador y los documentos personales
        return render_template(
    'view_worker.html',
    worker=worker,
    base_url=app.config['BASE_URL'],
    contract_types=contract_types,
    edit_mode=edit_mode,
    documentos=documentos,
    url_for=url_for,
    uploaded_files={f"{field}_file": worker.get(f"{field}_file") for field, _ in documentos},
    calculate_estado_documento=calculate_estado_documento,
    calculate_days_remaining=calculate_days_remaining,
    view_mode=True 
)

        
    return "Trabajador no encontrado"
    
@app.route('/update_contract_info/<string:id>', methods=['POST'])
def update_contract_info(id):
    worker = get_worker_by_id(id)
    if worker:
        # Obten los datos contractuales del formulario
        contract_commercial = request.form.get('contract_commercial')
        contract_type = request.form.get('contract_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        shift_type = request.form.get('shift_type')

        # Actualiza los datos contractuales del trabajador
        worker['contract_commercial'] = contract_commercial
        worker['contract_type'] = contract_type
        worker['start_date'] = start_date
        worker['end_date'] = end_date
        worker['shift_type'] = shift_type

        # Calcula la antigüedad laboral en años y meses
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        job_experience = relativedelta(today, start_date)
        years = job_experience.years
        months = job_experience.months

        # Almacena la antigüedad laboral en el diccionario del trabajador
        worker['job_experience'] = {'years': years, 'months': months}

        # Actualiza la lista de trabajadores con los cambios realizados
        update_workers_in_list(worker)

        # Redirige a la vista 'view_worker' para mostrar los cambios
        return redirect(f"{app.config['BASE_URL']}view_worker/{id}")

    return "Trabajador no encontrado", 404

def update_workers_in_list(updated_worker):
    for i, worker in enumerate(workers):
        if worker['id'] == updated_worker['id']:
            workers[i] = updated_worker
@app.route('/upload_photo/<string:id>', methods=['POST'])
def upload_photo(id):
    worker = get_worker_by_id(id)
    if worker:
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                worker['photo'] = filename
                return redirect(app.config['BASE_URL'] + 'view_worker/' + id)
        return "No se seleccionó un archivo de foto."
    return "Trabajador no encontrado"


@app.route('/add_contract_info/<string:id>', methods=['GET', 'POST'])
def add_contract_info(id):
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    # Obtener información del trabajador
    worker = get_worker_by_id(id)
    
    if worker:
        if request.method == 'POST':
            # Obtener datos del formulario
            contract_commercial = request.form.get('contract_commercial')
            contract_type = request.form.get('contract_type')
            start_date_str = request.form.get('start_date_str')
            end_date_str = request.form.get('end_date_str')
            shift_type = request.form.get('shift_type')
            
            # Convertir fechas a objetos datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

            # Actualizar información contractual del trabajador
            worker['contract_commercial'] = contract_commercial
            worker['contract_type'] = contract_type
            worker['start_date'] = start_date
            worker['end_date'] = end_date
            worker['shift_type'] = shift_type

            # Redirigir a la vista del trabajador después de guardar cambios
            return redirect(f"{app.config['BASE_URL']}view_worker/{id}")

        # Valores por defecto si no existen en el trabajador
        if 'contract_commercial' not in worker:
            worker['contract_commercial'] = ''
        if 'contract_type' not in worker:
            worker['contract_type'] = ''
        if 'start_date' not in worker:
            worker['start_date'] = None
        if 'end_date' not in worker:
            worker['end_date'] = None
        if 'shift_type' not in worker:
            worker['shift_type'] = ''

        # Renderizar el formulario con la información del trabajador
        return render_template('add_contract_info.html', worker=worker, base_url=app.config['BASE_URL'], contract_types=contract_types)

    return "Trabajador no encontrado"

def calculate_days_remaining(end_date_str):
    if isinstance(end_date_str, str):  # Verifica si es una cadena
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    elif isinstance(end_date_str, datetime):  # Si es un datetime, usa el objeto directamente
        end_date = end_date_str
    else:
        return None  # Manejo de caso inesperado

    today = datetime.now()
    if isinstance(end_date, datetime):  # Verifica si es un datetime
        days_remaining = (end_date - today).days
        return days_remaining
    else:
        return None  # Manejo de caso inesperado

@app.route('/add_personal_info/<string:id>', methods=['GET', 'POST'])

def add_personal_info(id):
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    worker = get_worker_by_id(id)
    documentos = [
            ('id_or_passport', 'Cedula de Identidad o Pasaporte'),
            ('id_or_contrato', 'Contrato de Trabajo'),
            ('id_or_anexo', 'Anexo de Trabajo'),
            ('id_or_odi', 'Obligación de Informar'),
            ('id_or_ocupacional', 'Exámenes de Salud'),
            ('id_or_mun', 'Licencia Municipal'),
            ('id_or_psico', 'Cert. Examen Psico-Sensométrico'),
            ('id_or_cmd', 'Curso Manejo a la Defensiva'),
            ('id_or_curso', 'Certificado o Curso Especifico por Cargo'),
            ('id_or_RIOHS', 'Comprobante entrega RIOHS'),
            ('id_or_EPP', 'Comprobante entrega EPP'),
            ('id_or_Teck', 'Inducción Teck'),
            ('id_or_ODI_CMP', 'Obligación de Informar CMP'),
        ]

    if worker:
        if request.method == 'POST':
            # Definimos una lista de documentos con sus respectivos nombres y campos
            estados = []
            
            # Iteramos sobre la lista de documentos para procesar cada uno
            for field, doc_name in documentos:
                start_date = request.form.get(f"{field}_start_date")
                end_date = request.form.get(f"{field}_end_date")
                tipo_alerta_dias = int(request.form.get(f"{field}_tipo_alerta_dias", 0))
                file = request.files.get(f"document_file_{field}")
                filename = save_file(file)
                if filename:
                    worker[f'{field}_file'] = filename

                # Guardamos el archivo si está presente
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join('uploads', filename))
                    worker[f'{field}_file'] = filename

                # Actualizamos las fechas en el diccionario del trabajador
                worker[f'{field}_start_date'] = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
                worker[f'{field}_end_date'] = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

                                
                worker[f'{field}_tipo_alerta_dias'] = tipo_alerta_dias

                tiempo_vencimiento = calculate_days_remaining(worker[f'{field}_end_date'])
                
                estado_alerta_dias = worker[f'{field}_tipo_alerta_dias']
                tiempo_vencimiento = int(tiempo_vencimiento) if tiempo_vencimiento else 0
                
                if tiempo_vencimiento > estado_alerta_dias:
                    estado_documento = 'Vigente'
                elif tiempo_vencimiento <= 0:
                    estado_documento = 'Vencido'
                else:
                    estado_documento = 'Próximo a Vencer'

                # Agregamos el estado del documento a la lista de estados
                estados.append(estado_documento)

            # Actualizamos la columna 'Estado' tomando el valor más crítico
            worker['estado'] = max(estados, key=lambda x: estados.index(x))

            # Redirige de nuevo a la vista 'view_worker' después de guardar los cambios
            return redirect(url_for('view_worker', id=worker['id']), code=303)
        
        formatted_dates = {}
        for field, _ in documentos:
            if isinstance(worker.get(field+'_start_date'), datetime) and worker[field+'_start_date']:
              formatted_dates[field+'_start_date'] = worker[field+'_start_date'].strftime('%Y-%m-%d')
            else:
              formatted_dates[field+'_start_date'] = 'No disponible'

            if isinstance(worker.get(field+'_end_date'), datetime) and worker[field+'_end_date']:
              formatted_dates[field+'_end_date'] = worker[field+'_end_date'].strftime('%Y-%m-%d')
            else:
              formatted_dates[field+'_end_date'] = 'No disponible'
            
            
        # Renderiza el formulario con los datos actuales del trabajador
        return render_template(
            'add_personal_info.html',
            worker=worker,
            documentos=documentos,
            base_url=app.config['BASE_URL'],
            url_for=url_for,
            uploaded_files={f"{field}_file": worker.get(f"{field}_file") for field, _ in documentos},
            calculate_estado_documento=calculate_estado_documento,
            calculate_days_remaining=calculate_days_remaining,
            formatted_dates=formatted_dates,
            view_mode=False 
        )
    
    return "Trabajador no encontrado"

def calculate_estado_documento(end_date_str, tipo_alerta_dias):
    if isinstance(end_date_str, datetime):
        today = datetime.now()
        days_remaining = (end_date_str - today).days

        if days_remaining is not None:  
            if days_remaining > tipo_alerta_dias:
                return 'Vigente'
            elif days_remaining <= 0:
                return 'Vencido'
            else:
                return 'Próximo a Vencer'
    elif isinstance(end_date_str, str):
        end_date = datetime.strptime(end_date_str, '%d-%m-%Y')
        today = datetime.now()
        days_remaining = (end_date - today).days

        if days_remaining is not None:  
            if days_remaining > tipo_alerta_dias:
                return 'Vigente'
            elif days_remaining <= 0:
                return 'Vencido'
            else:
                return 'Próximo a Vencer'
    return 'Sin datos'
# Y luego, en tu función de ruta, puedes pasar esta función a la plantilla
# ...
@app.route('/notifications')
@login_required
def notifications():
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    # Tu lógica actual para obtener los trabajadores y documentos...
    documentos = [
            ('id_or_passport', 'Cedula de Identidad o Pasaporte'),
            ('id_or_contrato', 'Contrato de Trabajo'),
            ('id_or_anexo', 'Anexo de Trabajo'),
            ('id_or_odi', 'Obligación de Informar'),
            ('id_or_ocupacional', 'Exámenes de Salud'),
            ('id_or_mun', 'Licencia Municipal'),
            ('id_or_psico', 'Cert. Examen Psico-Sensométrico'),
            ('id_or_cmd', 'Curso Manejo a la Defensiva'),
            ('id_or_curso', 'Certificado o Curso Especifico por Cargo'),
            ('id_or_RIOHS', 'Comprobante entrega RIOHS'),
            ('id_or_EPP', 'Comprobante entrega EPP'),
            ('id_or_Teck', 'Inducción Teck'),
            ('id_or_ODI_CMP', 'Obligación de Informar CMP'),
        ]
    # Filtrar los trabajadores cuyos documentos están próximos a vencer o ya vencidos
    workers_to_notify = []
    for worker in workers:
        for field, doc_name in documentos:
            tiempo_vencimiento = calculate_days_remaining(worker[f'{field}_end_date'])
            estado_documento = calculate_estado_documento(worker[f'{field}_end_date'], worker[f'{field}_tipo_alerta_dias'])
            if estado_documento in ['Próximo a Vencer', 'Vencido']:
                worker_data = {
                    'id': worker['id'],
                    'name': worker['name'],
                    'document': worker['document'],
                    'doc_name': doc_name,
                    'end_date': worker[f'{field}_end_date'],
                    'tiempo_vencimiento': tiempo_vencimiento,
                    'estado_documento': estado_documento
                    
                }
                workers_to_notify.append(worker_data)
    workers_to_notify = sorted(workers_to_notify, key=lambda x: x['tiempo_vencimiento'], reverse=True)
    return render_template('notifications.html', workers=workers, documentos=documentos, workers_to_notify=workers_to_notify)

@app.route('/view_personal_info/<string:id>', methods=['GET'])

def view_personal_info(id):
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    worker = get_worker_by_id(id)
    if worker:
        return render_template('view_personal_info.html', worker=worker, base_url=app.config['BASE_URL'])
    return "Trabajador no encontrado"

# Función para guardar archivos
def save_file(file):
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)  # Asegúrate de tener una carpeta 'uploads'
        print("File saved at:", file_path)  # Agrega esta línea para depuración
        return file_path
    return None

@app.route('/add_personal_info/<string:id>', methods=['GET', 'POST'])

def add_personal_infor(id):
    if 'logged_in' not in session:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('login'))
    worker = get_worker_by_id(id)
    documentos = [
            ('id_or_passport', 'Cedula de Identidad o Pasaporte'),
            ('id_or_contrato', 'Contrato de Trabajo'),
            ('id_or_anexo', 'Anexo de Trabajo'),
            ('id_or_odi', 'Obligación de Informar'),
            ('id_or_ocupacional', 'Exámenes de Salud'),
            ('id_or_mun', 'Licencia Municipal'),
            ('id_or_psico', 'Cert. Examen Psico-Sensométrico'),
            ('id_or_cmd', 'Curso Manejo a la Defensiva'),
            ('id_or_curso', 'Certificado o Curso Especifico por Cargo'),
            ('id_or_RIOHS', 'Comprobante entrega RIOHS'),
            ('id_or_EPP', 'Comprobante entrega EPP'),
            ('id_or_Teck', 'Inducción Teck'),
            ('id_or_ODI_CMP', 'Obligación de Informar CMP'),
        ]

    if worker:
        if request.method == 'POST':
            estados = []

            for field, doc_name in documentos:
                # Lógica para obtener las fechas y archivos actualizados

                tiempo_vencimiento = calculate_days_remaining(worker[f'{field}_end_date'])
                estado_documento = calculate_estado_documento(worker[f'{field}_end_date'], worker[f'{field}_tipo_alerta_dias'])
                if estado_documento in ['Próximo a Vencer', 'Vencido']:
                    estados.append(estado_documento)

            # Actualiza el estado del trabajador
            worker['estado'] = max(estados, key=lambda x: estados.index(x))

            # Redirige de nuevo a la vista 'view_worker' después de guardar los cambios
            return redirect(url_for('view_worker', id=worker['id']), code=303)

        # Renderiza el formulario con los datos actuales del trabajador
        return render_template(
            'add_personal_info.html',
            worker=worker,
            documentos=documentos,
            base_url=app.config['BASE_URL'],
            url_for=url_for,
            uploaded_files={f"{field}_file": worker.get(f"{field}_file") for field, _ in documentos},
            calculate_estado_documento=calculate_estado_documento,
            calculate_days_remaining=calculate_days_remaining,
            view_mode=False 
        )
    
    return "Trabajador no encontrado"
@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Elimina la clave 'logged_in' de la sesión
    session.pop('username', None)   # Elimina la clave 'username' de la sesión
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)