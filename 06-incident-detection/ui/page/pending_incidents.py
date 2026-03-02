import streamlit as st
from utils.apigw_handler import get_incidents, get_runbook, incident_remediate
from utils.init_session import reset_session
import pandas as pd
import json
from datetime import datetime as dt


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

def pending_incident_page():
    incidents = get_incidents("pending")
    if len(incidents) == 0 :
        dfall = pd.DataFrame(columns=["incidentActionTrace","incidentData","incidentStatus","incidentIdentifier","incidentRunbook","incidentTime","sk","incidentType","lastUpdateBy","pk","lastUpdate"])
    else:
        dfall = pd.DataFrame(incidents)   

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
            pass
        
        if st.button("All incidents"):
            st.session_state['page'] = 'all_incidents'
            st.rerun()
        
        if st.button("Logout"):
            reset_session()
            st.rerun()
        
        st.sidebar.image("image/powered_by_aws.png",width=120)  


    st.title(":orange[Pending incidents] ")
    st.subheader(f":orange[Metric Summary as of] :blue[{dt.now().now().strftime("%Y-%m-%d %H:%M:%S")}] ", divider=True)

    col1, col2, col3 = st.columns(3)
    col1.markdown(get_kpi("fa-solid fa-circle-exclamation","Total Pending Incidents",eventCount), unsafe_allow_html=True)
    col2.markdown(get_kpi("fa-solid fa-server","Total Unique Instance",instanceCount), unsafe_allow_html=True)
    col3.markdown(get_kpi("fa-solid fa-bell","Total Unique Alert Type",alertTypeCount), unsafe_allow_html=True)
    
    col4, col5 = st.columns([3,1])
    col4.markdown("### :orange[Incident Summary] ")

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
    #col4.markdown("#### Event Details")
    #col4.divider()
    #col5.markdown("#### User Action")
    col5.markdown("### :orange[User Action] ")

    col5.write("Here are the actions that requires manual user intervention")
    runbook_action = col5.button("Get Runbook")
    remediate_action = col5.button("Remediate Incident")

    col5.divider()
    rows = event['selection']['rows']
    pk = None
    description = None
    if len(rows) != 0:
        print(dfall)
        pk = dfall.iloc[rows[0]]['pk']
        description = json.loads(dfall.iloc[rows[0]]['incidentData'])['configuration']['description']
        print(pk)
        #col4.json(dfall.iloc[rows[0]].to_json(orient='records'))
 
    if runbook_action:
        if pk is None:
            col4.error("Please select an incident to get the runbook for the incident")
            return
        with col4.status("Retrieving incident runbook..."):
            runbook = get_runbook(pk,description)
            col4.markdown("***Runbook Instructions for " + pk + "***")
            col4.text_area("Runbook Instructions", runbook['runbook'],height=200, label_visibility="hidden")

    if remediate_action:
        if pk is None:
            col4.error("Please select an incident to auto-remediate the incident")
            return
        with col4.status("Remediating incident..."):
            incident = incident_remediate(pk,description)
            col4.markdown("***Status of auto remediation for " + pk + "***")
            col4.json(incident['result'])

