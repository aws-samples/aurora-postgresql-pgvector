import streamlit as st
from utils.apigw_handler import get_incidents, get_runbook, incident_remediate
from utils.init_session import reset_session
import pandas as pd
import json

def get_kpi(iconname, metricname, metricvalue):
    wch_colour_box = (0,204,102)
    wch_colour_font = (0,0,0)
    fontsize = 32
    valign = "left"
    lnk = '<link rel="stylesheet" href="https://use.fontawesome.com/releases/v6.6.0/css/all.css" crossorigin="anonymous">'

    htmlstr = f"""<p style='background-color: rgb({wch_colour_box[0]}, 
                                              {wch_colour_box[1]}, 
                                              {wch_colour_box[2]}, 0.75); 
                        color: rgb({wch_colour_font[0]}, 
                                   {wch_colour_font[1]}, 
                                   {wch_colour_font[2]}, 0.75); 
                        font-size: {fontsize}px; 
                        border-radius: 7px; 
                        padding-left: 12px; 
                        padding-top: 18px; 
                        padding-bottom: 18px; 
                        line-height:25px;'>
                        <i class='{iconname} fa-xs'></i> {metricvalue}
                        </style><BR><span style='font-size: 14px; 
                        margin-top: 0;'>{metricname}</style></span></p>"""
    return lnk + htmlstr      

def all_incident_page():
    incidents = get_incidents("all")
    if len(incidents) == 0 :
        dfall = pd.DataFrame(columns=["incidentActionTrace","incidentData","incidentStatus","incidentIdentifier","incidentRunbook","incidentTime","sk","incidentType","lastUpdateBy","pk","lastUpdate"])
    else:
        dfall = pd.DataFrame(incidents)   

    dfall = dfall.drop("incidentData" , axis=1)

    eventCount = len(incidents)
    instanceCount =  str(dfall['incidentIdentifier'].nunique())
    alertTypeCount =  str(dfall['incidentType'].nunique())
    
    st.set_page_config(page_title="DAT307-IDR: Amazon RDS Incidents", layout="wide")
    st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)
    with st.sidebar:
        st.sidebar.image("image/idr_logo.png")        
        st.subheader("DAT307 - Build a Generative AI incident detection and response system powered by Amazon Aurora")
        st.divider()
        
        if st.button("Pending incidents"):
            st.session_state['page'] = 'pending_incidents'
            st.rerun()       
        if st.button("All incidents"):
            pass       
        if st.button("Logout"):
            reset_session()
            st.rerun()
        
        st.sidebar.image("image/powered_by_aws.png",width=120)  


    st.title("All incidents")
    st.subheader("Metric Summary", divider=True)
    col1, col2, col3 = st.columns(3)
    col1.markdown(get_kpi("fa-solid fa-circle-exclamation","Total incidents",eventCount), unsafe_allow_html=True)
    col2.markdown(get_kpi("fa-solid fa-server","Total Unique Instance",instanceCount), unsafe_allow_html=True)
    col3.markdown(get_kpi("fa-solid fa-bell","Total Unique Alert Type",alertTypeCount), unsafe_allow_html=True)
    
    col4, col5 = st.columns([10,1])
    col4.markdown("#### Incident Summary")
    col4.write("Here are the list of active incidents")
    col4.write("Please select an incident to process by clicking the first column of the row")
    
    print("Display table output")
    print(dfall)
    event = col4.dataframe(dfall,
                             on_select="rerun",
                             selection_mode="single-row",
                             hide_index=True,
                             column_config={
                             "incidentType": "Incident Type",
                             "pk": "Session ID",
                             "incidentIdentifier": "Database Instance",
                             "incidentStatus": "Incident Status",
                             "incidentTime": "Incident Time"
                            },
                            column_order=("pk","incidentIdentifier","incidentType","incidentStatus","incidentTime")
    )
    col4.markdown("#### Event Details")
    col4.divider()
    rows = event['selection']['rows']
    if len(rows) != 0:
        print(dfall)
        col4.write("Runbook information")
        print(dfall.iloc[rows[0]]['incidentRunbook'])
        if dfall.iloc[rows[0]]['incidentRunbook'] != "None":
            col4.json(dfall.iloc[rows[0]]['incidentRunbook'])
        col4.write("Action trace")
        if dfall.iloc[rows[0]]['incidentActionTrace'] != "None":
            col4.json(dfall.iloc[rows[0]]['incidentActionTrace'])
 