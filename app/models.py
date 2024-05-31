# Define models of SQLAlchemy for PostgreSQL

from app import db
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz


class WC_Farms_Zones(db.Model):
    __tablename__ = 'wc_farms_zones'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    description = db.Column(db.Text)
    latitude = db.Column(db.Text)
    longitude = db.Column(db.Text)
    type = db.Column(db.Text)
    farmid = db.Column(db.Integer)
    pumpsystemid = db.Column(db.Float)
    kc = db.Column(db.Integer)
    theoreticalflowm3h = db.Column(db.Float)  
    efficiency = db.Column(db.Text)
    humidityretention = db.Column(db.Text)
    max = db.Column(db.Text)
    min = db.Column(db.Text)
    criticalpoint1 = db.Column(db.Text)
    criticalpoint2 = db.Column(db.Text)
    criticalpoint3 = db.Column(db.Text)
    criticalpoint4 = db.Column(db.Text)
    soilmode = db.Column(db.Text)
    crops = db.Column(db.Text)
    area_m2 = db.Column(db.Float)
    pumpids = db.Column(db.Text)
    predefinedpumps = db.Column(db.Text)
    irrigation_max = db.Column(db.Float)
    irrigation_min = db.Column(db.Float)
    irrigation_avg = db.Column(db.Float)
    irrigation_std = db.Column(db.Float)
    southwest_lng = db.Column(db.Float)
    southwest_lat = db.Column(db.Float)
    northeast_lng = db.Column(db.Float)
    northeast_lat = db.Column(db.Float)


class WCFarmsIrrigation(db.Model):
    __tablename__ = 'wc_farms_irrigation'

    id = db.Column(db.Integer, primary_key=True)
    inittime = db.Column(db.DateTime)
    endtime = db.Column(db.DateTime)
    status = db.Column(db.Text)
    irrigationtype = db.Column(db.Text)
    pumpsystemid = db.Column(db.Integer)
    pumpids = db.Column(db.Text)
    zoneid = db.Column(db.Integer)
    senttonetwork = db.Column(db.Boolean)
    scheduledtype = db.Column(db.Text)
    hydraulics = db.Column(db.Text)
    groupingname = db.Column(db.Text)
    volume_m3 = db.Column(db.Float)
    precipitation_mm = db.Column(db.Float)
    theoreticalflow_m3_h = db.Column(db.Float) 

class ExecutionLog(db.Model):
    __tablename__ = 'execution_log'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    status = db.Column(db.String(50))
    date = db.Column(db.DateTime(timezone = True), default=lambda: datetime.now(pytz.timezone('America/Santiago')))




