from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI()

# Configuración de la base de datos
DATABASE_URL = "sqlite:///./test.db"  # Cambia a tu URL de base de datos
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class GastoComunDB(Base):
    __tablename__ = "gastos_comunes"
    
    id = Column(Integer, primary_key=True, index=True)
    departamento_id = Column(Integer, index=True)
    departamento = Column(Integer)
    periodo = Column(String)
    monto = Column(Float)
    pagado = Column(Boolean, default=False)
    fecha_pago = Column(Date, nullable=True)

# Crea las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelos Pydantic
class GastoComún(BaseModel):
    departamento_id: int
    departamento: int
    periodo: str
    monto: float
    pagado: bool = False
    fecha_pago: Optional[date] = None

    class Config:
        orm_mode = True

class GenerarGastosRequest(BaseModel):
    año: int
    mes: Optional[int] = None
    departamentos: List[int]

class PagoRequest(BaseModel):
    departamento_id: int
    periodo: str
    fecha_pago: date

# Endpoint para generar gastos comunes
@app.post("/generar-gastos/")
def generar_gastos(request: GenerarGastosRequest, db: Session = Depends(get_db)):
    gastos_generados = []
    
    for depto_id in request.departamentos:
        meses = [request.mes] if request.mes else range(1, 13)
        for mes in meses:
            periodo = f"{request.año}-{str(mes).zfill(2)}"
            gasto = GastoComunDB(departamento_id=depto_id, departamento=depto_id, periodo=periodo, monto=100.0)
            db.add(gasto)
            db.commit()
            db.refresh(gasto)
            gastos_generados.append(gasto)
    
    return {"mensaje": "Gastos generados exitosamente", "gastos": gastos_generados}

# Endpoint para registrar un pago
@app.post("/pagar-gasto/")
def pagar_gasto(pago: PagoRequest, db: Session = Depends(get_db)):
    gasto = db.query(GastoComunDB).filter_by(departamento_id=pago.departamento_id, periodo=pago.periodo).first()
    
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    if gasto.pagado:
        return {"mensaje": "Pago duplicado", "estado": "Pago duplicado"}
    
    gasto.pagado = True
    gasto.fecha_pago = pago.fecha_pago
    db.commit()

    fecha_limite = datetime.strptime(f"{pago.periodo}-01", "%Y-%m-%d") + timedelta(days=30)
    estado_pago = "Pago exitoso dentro del plazo" if pago.fecha_pago <= fecha_limite.date() else "Pago exitoso fuera de plazo"
    
    return {
        "mensaje": f"Pago registrado correctamente: {estado_pago}",
        "departamento_id": pago.departamento_id,
        "periodo": pago.periodo,
        "fecha_pago": pago.fecha_pago,
        "estado": estado_pago
    }

# Endpoint para ver pagos realizados
@app.get("/ver-pagos/")
def ver_pagos(departamento_id: Optional[int] = None, periodo: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(GastoComunDB).filter(GastoComunDB.pagado == True)
    
    if departamento_id:
        query = query.filter(GastoComunDB.departamento_id == departamento_id)
    if periodo:
        query = query.filter(GastoComunDB.periodo == periodo)
    
    pagos = query.all()
    return {"pagos": pagos} if pagos else {"mensaje": "No se encontraron pagos para los parámetros proporcionados."}

# Endpoint para ver todos los gastos comunes
@app.get("/ver-gastos/")
def ver_gastos(departamento_id: Optional[int] = None, periodo: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(GastoComunDB)
    
    if departamento_id:
        query = query.filter(GastoComunDB.departamento_id == departamento_id)
    if periodo:
        query = query.filter(GastoComunDB.periodo == periodo)
    
    gastos = query.all()
    return {"gastos": gastos} if gastos else {"mensaje": "No se encontraron gastos para los parámetros proporcionados."}
