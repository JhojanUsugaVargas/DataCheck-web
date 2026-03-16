from fpdf import FPDF
import datetime

class PMPReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'REPORTE CONSOLIDADO PMP - ESTADO DE BASES DE DATOS', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, title, 0, 1, 'L', 1)
        self.ln(4)

    def draw_table(self, header, data, col_widths):
        self.set_font('Arial', 'B', 10)
        for i, h in enumerate(header):
            self.cell(col_widths[i], 7, h, 1, 0, 'C')
        self.ln()
        
        self.set_font('Arial', '', 9)
        for row in data:
            # Handle multi-line if needed, but for simplicity we use truncated cells
            for i, item in enumerate(row):
                text = str(item)[:50] if i < len(row)-1 else str(item)
                self.cell(col_widths[i], 6, text, 1)
            self.ln()
        self.ln(5)

def generate_pmp_pdf(data):
    pdf = PMPReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # 1. Info General
    pdf.set_font('Arial', '', 10)
    g = data['general']
    pdf.cell(0, 7, f"Servidor: {g['instance']}    Host: {g['host']}    Fecha: {g['date']}", 0, 1)
    pdf.cell(0, 7, f"Activo Desde: {g['startup']}", 0, 1)
    pdf.ln(10)
    
    # 2. Archivos Físicos
    pdf.chapter_title('INFORME DE ESPACIO Y ARCHIVOS FISICOS DE BASES DE DATOS')
    header = ['BASE DE DATOS', 'UBICACION', 'NOMBRE ARCHIVO', 'TAMAÑO (MB)']
    col_widths = [45, 90, 30, 25]
    rows = [[r['db'], r['location'], r['filename'], r['sizemb']] for r in data['db_files']]
    pdf.draw_table(header, rows, col_widths)
    
    # 3. Espacio Libre
    pdf.chapter_title('INFORME DE ESPACIO LIBRE')
    header = ['PARTICION', 'ESPACIO LIBRE (GB)']
    col_widths = [95, 95]
    rows = [[r['volume_mount_point'], r['freegb']] for r in data['disk_free']] if data['disk_free'] else [['N/A', 'N/A']]
    pdf.draw_table(header, rows, col_widths)
    
    # 4. Respaldos
    pdf.chapter_title('INFORME DE RESPALDOS REALIZADOS')
    header = ['FINALIZA EL RESPALDO', 'TIPO', 'BASE DE DATOS']
    col_widths = [60, 40, 90]
    rows = [[r['finishdate'], r['type'], r['db']] for r in data['backups']]
    pdf.draw_table(header, rows, col_widths)
    
    # 5. DBs Nuevas
    pdf.chapter_title('BASES DE DATOS NUEVAS')
    header = ['NOMBRE', 'FECHA DE CREACION']
    col_widths = [95, 95]
    rows = [[r['name'], r['create_date']] for r in data['new_dbs']]
    pdf.draw_table(header, rows, col_widths)
    
    # 6. Linked Servers
    pdf.chapter_title('LINKED SERVERS')
    header = ['NOMBRE SERVIDOR', 'PRODUCTO', 'ORIGEN DE DATOS']
    col_widths = [60, 40, 90]
    rows = [[r['name'], r['product'], r['data_source']] for r in data['linked_servers']]
    pdf.draw_table(header, rows, col_widths)
    
    # 7. Usuarios Nuevos
    pdf.chapter_title('NUEVOS USUARIOS CREADOS')
    header = ['USUARIO', 'CREADO']
    col_widths = [95, 95]
    rows = [[r['name'], r['create_date']] for r in data['new_users']]
    pdf.draw_table(header, rows, col_widths)
    
    # 8. Jobs Fallidos
    pdf.chapter_title('INFORME DE TAREAS FALLIDAS')
    header = ['NOMBRE JOB', 'FECHA', 'MENSAJE']
    col_widths = [50, 40, 100]
    rows = [[r['jobname'], r['rundate'], r['message']] for r in data['failed_jobs']]
    pdf.draw_table(header, rows, col_widths)
    
    # Return as bytes or save to path
    return pdf.output()
