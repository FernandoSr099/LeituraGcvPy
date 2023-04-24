import cx_Oracle
import pandas as pd
import sys, os, datetime
import tkinter as tk
import contextlib
from tkcalendar import DateEntry
from tkinter import ttk, messagebox, filedialog
from contextlib import contextmanager
from tkinter.font import Font
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from datetime import datetime

@contextmanager
def oracle_connection():
    global dsn, user, password, conn
    dsn = cx_Oracle.makedsn("144.22.158.19", "1521", service_name="methos.sub03111309520.vcnmethos.oraclevcn.com")
    user = "CAMPOVERDE"
    password = "Camp@!8872!@overde"
    conn = cx_Oracle.connect(user=user, password=password, dsn=dsn)
    try:
        yield conn
    finally:
        conn.close()

## Acessso ao  banco de dados Inicio

def consultar_banco_dados(pedido):
    with oracle_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT * FROM V_CONTR_CARGA WHERE  QTE_LIDA < QTE_CAIXAS AND PEDIDO = :PEDIDO''',pedido=pedido)
        result = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        return df

def desvincular_etiqueta():
    global desvincular
    desvincular = entrada_desvincular.get()
    entrada_desvincular.delete(0, tk.END)

    
    # Verifica se o campo de entrada está vazio
    if not entrada_desvincular:
        messagebox.showerror("Erro", "Campo de entrada vazio.")
        return
    
    # Verifica se a etiqueta está vinculada a um pedido
    with oracle_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM ETIQ_GCV WHERE SUP_ETIQLAB_ID=:etiqueta", etiqueta=desvincular)
        resultado = cursor.fetchone()[0]
    
    if resultado == 0:
        messagebox.showerror("Erro", "Etiqueta não encontrada no banco de dados.")
        return
    else:
        resposta = messagebox.askquestion("Confirmação", "Deseja realmente desvincular a etiqueta?")
        if resposta == "yes":
            # Remove a linha correspondente à etiqueta da tabela ETIQ_GCV
            with oracle_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE ETIQ_GCV WHERE SUP_ETIQLAB_ID = :etiqueta", etiqueta=desvincular)
                messagebox.showinfo("Sucesso", "Etiqueta desvinculada com sucesso.")
                conn.commit()

        else:
            return 

# def insertetiqueta():
    with oracle_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''		 
            INSERT INTO ETIQ_GCV
            (SUP_ETIQLAB_ID, SUP_ITEMCONTROLE_ID, ID_PEDIDO_PRODUTO, QTE)
            SELECT
                :ETIQUETA,
                IT.SUP_ITEMCONTROLE_ID,
                P.ID_PRODUTO,
                1
            FROM
                SUP_MOVITEM MOV
                INNER JOIN SUP_ITCONTR_MOVIT IT ON MOV.SUP_MOVITEM_ID = IT.SUP_MOVITEM_ID
                INNER JOIN NFE_DOC_PRODUTOS P ON P.COD_PRODUTO = MOV.MAN_ITEM_ID
                INNER JOIN NFE_DOC N ON N.ID_NFE = P.ID_NFE
            WHERE
                MOV.TIPODOC = 'ETIQ'
                AND MOV.NUMDOC = :ETIQUETA
                AND MOV.TIPOENTSAI = 'E'
                AND MOV.SUP_HISTMOVITEM_ID = 142
                AND N.NR_REFERENCIA = :PEDIDO
                AND N.SERIE = 'PED'
            ''', etiqueta=etiqueta, pedido=pedido)
        conn.commit()

def etiqueta_existe(etiqueta):
        with oracle_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT count(*) FROM ETIQ_GCV WHERE SUP_ETIQLAB_ID=:ETIQUETA''', etiqueta=etiqueta)
            resultado = cursor.fetchall()
            count = resultado == 1
            return count

def etiqueta_cadastrada(etiqueta):
        with oracle_connection() as conn:
            resultado = conn.cursor()
            resultado.execute("""SELECT COUNT(*) FROM SUP_MOVITEM WHERE NUMDOC = :ETIQUETA AND TIPOENTSAI = 'E' AND TIPODOC = 'ETIQ' AND SUP_HISTMOVITEM_ID=142
            """, etiqueta=etiqueta)
            count = resultado = 0
            return count

def pedido_existe(pedido):
    with oracle_connection() as conn: 
        resultado = conn.cursor()
        resultado.execute(''' 
        SELECT COUNT(*) QTE
       FROM COM_CARGAPEDIDO CP 
         INNER JOIN COM_CARGA C ON CP.COM_CARGA_ID = C.COM_CARGA_ID
         INNER JOIN COM_CARGAITEM CI ON CI.ID_NFE = CP.ID_NFE
         INNER JOIN NFE_DOC_PRODUTOS P ON CI.ID_NFE = P.ID_NFE AND CI.ID_DOC_PRODUTOS = P.ID_DOC_PRODUTOS
         INNER JOIN MAN_ITEM MI      ON P.COD_PRODUTO = MI.MAN_ITEM_ID
         INNER JOIN NFE_DOC NF   ON CI.ID_NFE = NF.ID_NFE
         WHERE NF.NR_REFERENCIA = :pedido AND CI.INDFATURADO = 'N'
        ''', pedido=pedido)
        count = resultado.fetchone()[0] > 0
        return count

def saldo_item(pedido, etiqueta):
    with oracle_connection() as conn:
        resultado = conn.cursor()
        resultado.execute(''' SELECT  (QTE_CAIXAS - QTE_LIDA )AS SALDO FROM V_CONTR_CARGA WHERE PEDIDO = :PEDIDO 
                        AND MAN_ITEM_ID = (SELECT MAN_ITEM_ID FROM SUP_MOVITEM WHERE NUMDOC = :ETIQUETA AND TIPOENTSAI = 'E' AND TIPODOC = 'ETIQ')
        ''' , pedido=pedido, etiqueta=etiqueta)
        count = resultado = 0
        return count

def pesquisar_lote(treeview, entrada_pesquisa_lote):
    with oracle_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
                '''SELECT COUNT(*) AS QTE, MAX(NF.NR_REFERENCIA) AS PEDIDO,MAX(PE.RAZAOSOCIAL) AS CLIENTE,MAX(DESCRICAO) AS PRODUTO, MAX(MO.LOTE_INFO) AS LOTE FROM ETIQ_GCV E 
         INNER JOIN NFE_DOC_PRODUTOS P ON E.ID_PEDIDO_PRODUTO = P.ID_PRODUTO
         INNER JOIN NFE_DOC NF         ON P.ID_NFE = NF.ID_NFE  
         INNER JOIN SUP_MOVITEM MO     ON MO.NUMDOC =  TO_CHAR(E.SUP_ETIQLAB_ID) AND MO.TIPODOC = 'APUR' AND MO.TIPOENTSAI = 'E'
         INNER JOIN SIS_PESSOA PE      ON PE.SIS_PESSOA_ID = NF.CLIENTE      
        WHERE MO.LOTE_INFO = :LOTE
        GROUP BY NF.NR_REFERENCIA,MO.LOTE_INFO
                    ''',
            
            lote = entrada_pesquisa_lote)
        result = cursor.fetchall()
        global df_pesquisa
        columns = [i[0] for i in cursor.description]
        df_pesquisa = pd.DataFrame(result, columns=columns)
        atualizar_treeview_pesquisa(treeview)
        return df_pesquisa
    
def pesquisar_data(treeview):
    with oracle_connection() as conn:
        cursor = conn.cursor()
        data_pesquisa = entrada_pesquisa_data.get()
        data_pesquisa = datetime.strptime(data_pesquisa, '%d/%m/%Y')
        cursor.execute(
                '''SELECT LOTE_INFO,SUM(LIDAS) AS LIDAS ,SUM(APURADAS) AS APURADAS ,SUM(NOTAS) AS NOTAS, (SUM(APURADAS) - SUM(NOTAS)) AS PENDENTE,(SUM(LIDAS) - SUM(NOTAS) - (SUM(APURADAS) - SUM(NOTAS))) AS SALDO  FROM (
                    SELECT LOTE_INFO,SUM(QTE) AS  LIDAS,0 AS APURADAS,0 AS NOTAS FROM SUP_MOVITEM WHERE DATA  = :DATA AND TIPODOC = 'ETIQ' GROUP BY LOTE_INFO 
                    UNION       
                    SELECT LOTE_INFO,0 AS LIDAS, SUM(QTE) AS  APURADAS, 0 AS NOTAS FROM SUP_MOVITEM WHERE DATA  = :DATA AND TIPODOC = 'APUR' AND TIPOENTSAI = 'E' GROUP BY LOTE_INFO 
                    UNION
                    SELECT LOTE_INFO,0 AS LIDAS, 0 AS APURADAS,SUM(QTE) AS  NOTAS  FROM SUP_MOVITEM WHERE DATA  = :DATA AND TIPODOC = 'NFS' AND TIPOENTSAI = 'S' AND LOTE_INFO IS NOT NULL  GROUP BY LOTE_INFO  
                    ) GROUP BY LOTE_INFO
                    ''',            
            DATA=data_pesquisa)
        result = cursor.fetchall()
        global df_pesquisa
        columns = [i[0] for i in cursor.description]
        df_pesquisa = pd.DataFrame(result, columns=columns)
        atualizar_treeview_pesquisa(treeview) 
        return df_pesquisa
    
def item_existe_pedido(pedido):
    with oracle_connection() as conn:
        resultado = conn.cursor()
        resultado.execute('''
        SELECT COUNT(*) QTE
        FROM COM_CARGAPEDIDO CP 
            INNER JOIN COM_CARGA C ON CP.COM_CARGA_ID = C.COM_CARGA_ID
            INNER JOIN COM_CARGAITEM CI ON CI.ID_NFE = CP.ID_NFE
            INNER JOIN NFE_DOC_PRODUTOS P ON CI.ID_NFE = P.ID_NFE AND CI.ID_DOC_PRODUTOS = P.ID_DOC_PRODUTOS
            INNER JOIN MAN_ITEM MI      ON P.COD_PRODUTO = MI.MAN_ITEM_ID
            INNER JOIN NFE_DOC NF   ON CI.ID_NFE = NF.ID_NFE
            WHERE NF.NR_REFERENCIA = :pedido AND CI.INDFATURADO = 'N' 
            AND   TRIM(MI.MAN_ITEM_ID) IN (SELECT MAN_ITEM_ID FROM SUP_MOVITEM WHERE NUMDOC = :ETIQUETA AND TIPOENTSAI = 'E' AND TIPODOC = 'ETIQ')
        ''', etiqueta=etiqueta, pedido=pedido)
        count = resultado == 0
        return count

## Aessso ao  banco de dados Fim

def limpar_treeview(treeview):
    children = treeview.get_children()
    if children:
        treeview.delete(*children)

def atualizar_treeview(treeview, df):
    #Define as colunas
    treeview["columns"] = list(df.columns)
    treeview.column("#0", width=0, stretch=tk.NO)
    for column in df.columns:
        treeview.column(column, width=60, anchor=tk.W)
        treeview.heading(column, text=column, anchor=tk.W)
   
  
    # Cria um estilo personalizado
    style = ttk.Style()
    style.configure("Custom.Treeview", 
                    background="green", 
                    foreground="white",
                    font=("Arial", 24),
                    rowheight=40)
    
    # Aplica o estilo personalizado ao treeview
    treeview.config(style="Custom.Treeview")
    
    # Limpa dados antigos do treeview
    treeview.delete(*treeview.get_children())    
    #Adiciona as linhas
    for i, row in df.iterrows():
        treeview.insert("", i, text="", values=list(row))     

def atualizar_treeview_pesquisa(treeview):
    #Define as colunas
    treeview["columns"] = list(df_pesquisa.columns)
    treeview.column("#0", width=0, stretch=tk.NO)
    for column in df_pesquisa.columns:
        treeview.column(column, width=100, anchor=tk.W)
        treeview.heading(column, text=column, anchor=tk.W)
  # limpa dados antigos do treeview
    treeview.delete(*treeview.get_children())    
    #Adiciona as linhas
    for i, row in df_pesquisa.iterrows():
        treeview.insert("", i, text="", values=list(row))

def consulta_pedido():
        global pedido
        pedido = entrada_pedido.get()
        if pedido_existe(pedido):
            df = consultar_banco_dados(pedido)
            atualizar_treeview(treeview, df)
            entrada_etiqueta.focus()

        else:
            messagebox.showerror("Erro", "Pedido não encontrado.")
            entrada_pedido.delete(0, tk.END)
            limpar_treeview(treeview)
            #entrada_pedido.focus()

def inserir_etiqueta():
    global etiqueta
    etiqueta = entrada_etiqueta.get()
    entrada_etiqueta.delete(0, tk.END)

    if not etiqueta:  # Verifica se a variável etiqueta não está vazia
         messagebox.showerror("Erro", "Etiqueta não poder ser Vazia")
         return
          
    if etiqueta_cadastrada(etiqueta):
        messagebox.showerror("Erro", "Etiqueta não registrada!")
        return
    
    if item_existe_pedido(pedido):
        messagebox.showerror("Erro", "Item não cadastrado neste pedido!")
        return

    if etiqueta_existe(etiqueta):
        messagebox.showerror("Erro", "A Etiqueta já foi vinculada a um Pedido")
        return
    
    if saldo_item(pedido, etiqueta):
        messagebox.showerror("Erro","Quantidade de ITEM ja atendida no pedido!")
        return

    entrada_etiqueta.delete(0, tk.END)
    insertetiqueta()
    consulta_pedido()

def on_enter_pressed(event):  
    global df
    inserir_etiqueta()
    atualizar_treeview()
    entrada_etiqueta.bind('<Return>', on_enter_pressed)

def on_entry_focusout(event):
    consulta_pedido()

def salvar_resultado():
    filename = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")])
    if filename:
        df_pesquisa.to_excel(filename, index=False)

def export_to_pdf(treeview):
    # Define o nome do arquivo
    filename = datetime.now().strftime("Relatório de Lotes_%d-%m-%Y_%H-%M-%S.pdf")
    nome_arquivo = filename

    # Cria o arquivo PDF
    pdf = SimpleDocTemplate(filename, pagesize=A4)

    # Define o estilo da tabela
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4CAF50")),
        ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 14),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ])

    # Define o estilo do título
    title_style = ParagraphStyle(
        name='title_style',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.black,
        alignment=1
    )

    # Define o estilo do subtítulo
    subtitle_style = ParagraphStyle(
        name='subtitle_style',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.black,
        alignment=1
    )

    # Define os estilos para as células da tabela
    cell_style = ParagraphStyle(
        name='cell_style',
        fontName='Helvetica',
        fontSize=10,
        leading=12,
        textColor=colors.black
    )

    # Define os dados da tabela
    data = []
    column_indices = {column: i for i, column in enumerate(treeview["columns"])}
    for item in treeview.get_children():
        values = []
        for column in treeview["columns"]:
            values.append(treeview.item(item)["values"][column_indices[column]])
        data.append(values)


    # Define o título do relatório
    title = Paragraph(f'Relatório de Lotes')

    # Define o subtítulo do relatório
    subtitle = Paragraph(f'Total de Lotes: {len(data)}', subtitle_style)

    # Cria uma lista com os dados da tabela formatados
    table_data = []
    for item in data:
        row_data = [Paragraph(str(cell_data), cell_style) for cell_data in item]
        table_data.append(row_data)

    # Cria a tabela com os dados formatados
    table = Table(table_data, repeatRows=1)

    # Define o estilo da tabela
    table.setStyle(style)

    # Adiciona o título, subtítulo e tabela ao PDF
    elements = [title, subtitle, table]

    # Cria o PDF
    pdf.build(elements)
    messagebox.showinfo("Concluído", f"O relatório {nome_arquivo}.pdf foi gerado com sucesso!")

#Criação de Telas
def tela_pesquisa():
    janela_pesquisa = tk.Toplevel(root)
    janela_pesquisa.title("Pesquisar Lotes")
    janela_pesquisa.geometry("800x600")
    janela_pesquisa.iconbitmap("jumbinho.ico")

    #Cria uma Treeview para exibir os dados
    treeview = ttk.Treeview(janela_pesquisa)
    treeview.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    #Frame Pesquisa
    frame_pesquisa = tk.Frame(janela_pesquisa)
    frame_pesquisa.pack(padx=10, pady=10)

    Frame_superior_pesquisa = tk.Frame(root, padx=10, pady=10, bg="#F0F0F0")
    Frame_superior_pesquisa.pack(side=tk.TOP)

    #CriaLabel e Entry e botão de pesquisa
    label_pesquisa_lote = tk.Label(frame_pesquisa,text="Pesquisar lote:", font= ("Arial", 12))
    label_pesquisa_lote.grid(row=0,column=0, padx=5, pady=5)
    
    
    global entrada_pesquisa_lote
    entrada_pesquisa_lote = tk.Entry(frame_pesquisa, width= 20, font=("Arial", 12))
    entrada_pesquisa_lote.grid(row=0, column=1, padx=5, pady=5)
    botao_pesquisa_lote = tk.Button(frame_pesquisa, text="Pesquisar por lote", command=lambda: pesquisar_lote(treeview, entrada_pesquisa_lote.get()), bg="green", fg="white")
    botao_pesquisa_lote.grid(row=0,column=2, padx=60, pady=5)
    
    #Botão Salvar em Excel
    botao_salvar = tk.Button(janela_pesquisa, text="Salvar em Excel", command=salvar_resultado)
    botao_salvar.pack(side="left", padx=5, pady=5)

 
    #Botão Salvar em PDF
    botao_salvar_pdf = tk.Button(janela_pesquisa, text="Salvar em PDF", command=lambda: export_to_pdf(treeview))
    botao_salvar_pdf.pack(side="left", padx=5, pady=5)

    #Botão Data
    
    label_pesquisa_data = tk.Label(frame_pesquisa,text="Pesquisar por data:", font= ("Arial", 12))
    label_pesquisa_data.grid(row=1,column=0, padx=5, pady=5)

    global entrada_pesquisa_data
    entrada_pesquisa_data = DateEntry(frame_pesquisa, width=12, background='darkblue', foreground='white', borderwidth=2, year=2023)
    entrada_pesquisa_data.config(date_pattern='dd/mm/yyyy')
    entrada_pesquisa_data.grid(row=1, column=1, padx=5, pady=5)

    

    botao_pesquisa_data = tk.Button(frame_pesquisa, text="Pesquisar por data", command=lambda: pesquisar_data(treeview), bg="green", fg="white")
    botao_pesquisa_data.grid(row=1,column=2, padx=60, pady=5)
    
    # Cria um widget Treeview para exibir os dados dos pedidos
    janela_pesquisa.treeview = treeview
    janela_pesquisa.transient(root)
    janela_pesquisa.grab_set() 
    janela_pesquisa.mainloop()

def tela_desvincular():
    janela_desvincular = tk.Toplevel(root)
    janela_desvincular.title("Desvincular Etiqueta")
    janela_desvincular.geometry("400x150")
    janela_desvincular.iconbitmap("jumbinho.ico")

    #Frame Desvincular
    frame_desvincular = tk.Frame(janela_desvincular)
    frame_desvincular.pack(padx=10, pady=10)
    # Cria um label e um entry para o número da etiqueta que será desvinculada
    label_desvincular = tk.Label(frame_desvincular, text="Etiqueta a ser desvinculada:", font=("Arial", 12))
    label_desvincular.grid(row=2, column=0, padx=5, pady=5)
    # label_desvincular.pack()
    global entrada_desvincular
    entrada_desvincular = tk.Entry(frame_desvincular, width=20, font=("Arial", 12))
    entrada_desvincular.grid(row=2, column=1, padx=5, pady=5)
    # Cria um botão para desvincular a etiqueta no banco de dados
    botao_desvincular_etiqueta = tk.Button(janela_desvincular, text="Desvincular Etiqueta", command=desvincular_etiqueta, bg="green", fg="white")
    botao_desvincular_etiqueta.pack(padx=5, pady=5)
    #botao_desvincular_etiqueta.grid(row=1, column=00, padx=5, pady=5)
    # botao_desvincular_etiqueta.pack()
    janela_desvincular.transient(root) # torna a janela de desvincular etiqueta dependente da janela principal
    janela_desvincular.grab_set() # torna a janela de desvincular etiqueta uma janela modal
    janela_desvincular.mainloop()

# Cria a janela principalroot = tk.Tk()
root = tk.Tk()
root.geometry("800x600")
root.iconbitmap("jumbinho.ico")
root.title("CONTROLE SAIDA DE ESTOQUE")
root.configure(bg="#F0F0F0")

# Cria um frame para o cabeçalho
header_frame = tk.Frame(root, bg="#2E8B57")
header_frame.pack(side=tk.TOP, fill=tk.X)

# Adiciona um título ao cabeçalho
titulo_label = tk.Label(header_frame, text="CONTROLE SAIDA DE ESTOQUE", font=("Arial", 20), fg="white", bg="#2E8B57")
titulo_label.pack(padx=10, pady=10)

# Define as cores usadas na interface
cor_botao = "#4CAF50"
cor_letra_botao = "white"
cor_label = "#444444"
cor_letra_label = "white"
cor_entry = "white"
cor_treeview = "#EEEEEE"
cor_letra_treeview = "#444444"
fonte_padrao = ("Helvetica", 14)

# Cria um widget Treeview para exibir os dados dos pedidos
treeview = ttk.Treeview(root, style="Custom.Treeview")
treeview.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

# Define o estilo do Treeview
style = ttk.Style(root)
style.theme_use("clam")
style.configure("Custom.Treeview", background=cor_treeview, fieldbackground=cor_treeview, foreground=cor_letra_treeview, rowheight=25, font=fonte_padrao)
style.map("Custom.Treeview", background=[("selected", "#4CAF50")], foreground=[("selected", "white")], highlightcolor=[("selected", "#4CAF50")])

# Cria um frame para os widgets de entrada de dados
frame_superior = tk.Frame(root, padx=10, pady=10, bg="#F0F0F0")
frame_superior.pack(side=tk.TOP)

# Cria um label e um entry para o número do pedido
label_pedido = tk.Label(frame_superior, text="Pedido:", font=fonte_padrao, bg=cor_label, fg=cor_letra_label)
label_pedido.grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
entrada_pedido = tk.Entry(frame_superior, width=20, font=fonte_padrao, bg=cor_entry)
entrada_pedido.grid(row=0, column=1, padx=5, pady=5)
entrada_pedido.focus()

# Cria um botão para consultar os pedidos no banco de dados
fontawesome = Font(family="FontAwesome", size=14)
botao_capturar = tk.Button(frame_superior, text="Consultar Pedidos", command=consulta_pedido, bg=cor_botao, fg=cor_letra_botao, font=fontawesome)
botao_capturar.grid(row=0, column=2, padx=5, pady=5)

# Cria um label e um entry para o número da etiqueta
label_etiqueta = tk.Label(frame_superior, text="Etiqueta:", font=fonte_padrao, bg=cor_label, fg=cor_letra_label)
label_etiqueta.grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
entrada_etiqueta = tk.Entry(frame_superior, width=20, font=fonte_padrao, bg=cor_entry)
entrada_etiqueta.grid(row=1, column=1, padx=5, pady=5)
entrada_etiqueta.bind('<Return>', on_enter_pressed)

# Cria um botão para inserir a etiqueta no banco de dados
botao_inserir_etiqueta = tk.Button(frame_superior, text="Inserir Etiqueta", command=inserir_etiqueta, bg=cor_botao, fg=cor_letra_botao, font=fontawesome)
botao_inserir_etiqueta.grid(row=1, column=2, padx=5, pady=5)

# Botão Tela desvincular
botao_desvincular_etiqueta = tk.Button(frame_superior, text="Desvincular Etiqueta", command=tela_desvincular, bg="#2E8B57", fg="white", font=("Arial", 12))
botao_desvincular_etiqueta.grid(row=0, column=6, padx=60, pady=5)

# Botão Tela Pesquisa
botao_pesquisa_lote = tk.Button(frame_superior, text="Pesquisar lote", command=tela_pesquisa, bg="#2E8B57", fg="white", font=("Arial", 12))
botao_pesquisa_lote.grid(row=1,column=6, padx=60, pady=5)

# Inicia o loop principal da janela
root.mainloop()
