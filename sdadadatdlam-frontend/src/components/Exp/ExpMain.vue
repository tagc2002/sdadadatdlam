<template>
    <ExpHeader/>
    <v-container>
        <v-row>
            <v-col class=expCard>
                <v-card>
                    <v-card-title>Partes</v-card-title>
                    <v-container class="mt-0 pt-0">
                        <v-row class="ma-0 pa-0 align-center " justify="center">
                            <v-col class="ma-0 pa-1">Nombre</v-col>
                            <v-col class="ma-0 pa-1 colLimit" cols="1">Tipo</v-col>
                            <v-col class="ma-0 pa-1 colLimit" cols="2" >CUIT</v-col>
                            <v-col class="ma-0 pa-1 colLimit" >Domicilio</v-col>
                            <v-col class="ma-0 pa-1">Representad@ por</v-col>
                            <v-col cols="auto" class="ma-0 pa-1 ml-5 pl-4"/>
                        </v-row>
                        <v-row v-for="parte in partes" class="ma-0 pa-0 align-center flex-nowrap">
                            <v-col class="ma-0 pa-1 infocol">{{ parte.nombre }}</v-col>
                            <v-col class="ma-0 pa-1 colLimit infocol" cols="1">{{ parte.tipo }}</v-col>
                            <v-col class="ma-0 pa-1 colLimit infocol" cols="2">{{ parte.cuit }}</v-col>
                            <v-col class="ma-0 pa-1 colLimit infocol">{{ parte.domicilio }}</v-col>
                            <v-col class="ma-0 pa-1 infocol">{{ parte.letri }}</v-col>
                            <v-col class="justify-end ma-0 pa-1 infocol" cols=auto>
                               <v-btn icon="mdi-pencil" density=default variant=tonal height="32px" width="32px" class="justify-self-center"/>
                            </v-col>
                        </v-row>
                    </v-container>
                </v-card>
            </v-col>  
            <v-col class=expCard>
                <v-card>
                    <v-card-title>Letrados</v-card-title>
                    <v-container class="mt-0 pt-0">
                        <v-row class="ma-0 pa-0 align-center " justify="center">
                            <v-col class="ma-0 pa-1">Nombre</v-col>
                            <v-col class="ma-0 pa-1">Tomo-folio</v-col>
                            <v-col class="ma-0 pa-1">Telefono</v-col>
                            <v-col class="ma-0 pa-1">Mail</v-col>
                            <v-col class="ma-0 pa-1">Estudio</v-col>
                            <v-col class="ma-0 pa-1">Asignado a</v-col>
                            <v-col cols="auto" class="ma-0 pa-1 ml-5 pl-4"/>
                        </v-row>
                        <v-row v-for="letri in letris" class="ma-0 pa-0 align-center flex-nowrap">
                            <v-col class="ma-0 pa-1 infocol">{{ letri.nombre }}</v-col>
                            <v-col class="ma-0 pa-1 infocol">{{ letri.tf }}</v-col>
                            <v-col class="ma-0 pa-1 infocol">{{ letri.telefono }}</v-col>
                            <v-col class="ma-0 pa-1 infocol">{{ letri.mail }}</v-col>
                            <v-col class="ma-0 pa-1 infocol">{{ letri.estudio }}</v-col>
                            <v-col class="ma-0 pa-1 infocol">{{ letri.asig }}</v-col>
                            <v-col class="justify-end ma-0 pa-1 infocol" cols=auto>
                               <v-btn icon="mdi-pencil" density=default variant=tonal height="32px" width="32px" class="justify-self-center"/>
                            </v-col>
                        </v-row>
                    </v-container>
                </v-card>
            </v-col>
            <v-col class="expCard">
                <v-card>
                    <v-card-title>Audiencias</v-card-title>
                    <v-container class="mt-0 pt-0">
                        <v-row class="ma-0 pa-0 align-center">
                            <div style="width:32px"></div>
                            <v-col cols="3" class="ma-0 pa-1">Fecha</v-col>
                            <v-col cols="1" class="ma-0 pa-1 colNoBreak">Tipo</v-col>
                            <v-col cols="2" class="ma-0 pa-1">Estado</v-col>
                            <v-col cols="4" class="ma-0 pa-1">Notas</v-col>
                            <v-col></v-col>
                        </v-row>
                        <v-row v-for="audiencia in audiencias" class="ma-0 pa-1 align-center flex-nowrap">
                            <v-container class="pa-0 ma-0">
                                <v-row class="pa-0 ma-0 align-center">
                                    <v-col class="ma-0 pa-1 pr-0 flex-grow-0">
                                        <v-btn :icon="notifMenuIcon(audiencia)" size="24px" variant="tonal" @click="toggleNotification(audiencia)"/>
                                    </v-col>
                                    <v-col cols="3" class="ma-0 pa-1 colLimit colNoBreak">{{ audiencia.fecha.toLocaleString("es-AR") }}</v-col>
                                    <v-col cols="1" class="ma-0 pa-1 colNoBreak">{{ audiencia.tipo }}</v-col>
                                    <v-col cols="2" class="ma-0 pa-1 colNoBreak">{{ audiencia.estado }}</v-col>
                                    <v-col class="ma-0 pa-1 infocol">{{ audiencia.notas }}</v-col>
                                    <v-col cols="auto" class="justify-end ma-0 pa-1">
                                        <v-btn icon="mdi-magnify" size="32px" variant="tonal" density="default"/>
                                    </v-col>
                                </v-row>
                                <v-row v-if="audiencia.toggleNotif" class="ma-0 pa-0">
                                    <v-col class="ma-0 pa-0">
                                        <v-card elevation="10" class="ma-2 mt-0 pt-0">
                                            <v-card-title>Notificaciones</v-card-title>
                                            <v-container class="ma-2 pa-0">
                                                <v-row class="ml-0 pa-0 align-center flex-nowrap">
                                                    <v-col>Persona</v-col>
                                                    <v-col>Tipo</v-col>
                                                    <v-col>Emision</v-col>
                                                    <v-col>Recepcion</v-col>
                                                    <v-col>Estado</v-col>
                                                </v-row>
                                                <v-row v-for="notif in notifications" class="ma-0 pa-0 align-center flex-nowrap">
                                                    <v-col>{{ notif.nombre }}</v-col>
                                                    <v-col>{{ notif.tipo }}</v-col>
                                                    <v-col>{{ notif.emision.toLocaleDateString("es-AR") }}</v-col>
                                                    <v-col>{{ notif.recepcion.toLocaleDateString("es-AR") }}</v-col>
                                                    <v-col>{{ notif.estado }}</v-col>
                                                </v-row>
                                            </v-container>
                                        </v-card>
                                    </v-col>
                                </v-row>
                            </v-container>
                        </v-row>
                    </v-container>
                </v-card>
            </v-col>
            <v-col class="expCard">
                <v-card>
                    <v-card-title>Resultados</v-card-title>
                    <v-container class="mt-0 pt-0">
                        <v-row class="ma-0 pa-0 align-center">
                            <v-col>Tipo</v-col>
                            <v-col>Fecha</v-col>
                            <v-col>Estado</v-col>
                            <v-col cols="auto">Accion</v-col>
                        </v-row>
                        <v-row v-for="result in resultados" class="ma-0 pa-0 align-center flex-nowrap">
                            <v-container class="pa-0 ma-0">
                                <v-row class="pa-0 ma-0 align-center">
                                    <v-col class="ma-0 pa-1">{{ result.fecha.toLocaleDateString("es-AR") }}</v-col>
                                    <v-col class="ma-0 pa-1">{{ result.tipo }}</v-col>
                                    <v-col class="ma-0 pa-1">{{ result.estado }}</v-col>
                                    <v-col cols=auto class="justify-end ma-0 pa-1">
                                        <v-btn icon="mdi-magnify" size="32px" variant="tonal" density="default"/>
                                    </v-col>
                                </v-row>
                            </v-container>
                        </v-row>
                    </v-container>
                </v-card>
            </v-col>
            <v-col class="expCard">
                <v-card>
                    <v-card-title>Documentacion</v-card-title>
                    <v-container class="mt-0 pt-0">
                        <v-row class="ma-0 pa-0 align-center flex-nowrap">
                            <v-col class="infocol">Tipo</v-col>
                            <v-col class="infocol">Asociada a</v-col>
                            <v-col class="infocol">Fecha</v-col>
                            <v-col class="infocol">Requerida</v-col>
                            <v-col class="infocol">En SECLO</v-col>
                            <v-col class="infocol">Subir SECLO</v-col>
                            <v-col class="infocol" cols="auto">Accion</v-col>
                        </v-row>
                        <v-row v-for="doc in docs" class="ma-0 pa-0 align-center flex-nowrap">
                            <v-col class="ma-0 pa-1">{{ doc.tipo }}</v-col>
                            <v-col class="ma-0 pa-1">{{ doc.asoc }}</v-col>
                            <v-col class="ma-0 pa-1">{{ doc.fecha?.toLocaleDateString() }}</v-col>
                            <v-col class="ma-0 pa-1">{{ doc.requerida ? "Si" : "No" }}</v-col>
                            <v-col class="ma-0 pa-1">{{ doc.SECLO ? "Si" : "No" }}</v-col>
                            <v-col class="ma-0 pa-1">{{ doc.subirSECLO ? "Si" : "No" }}</v-col>
                            <v-col cols=auto class="justify-end ma-0 pa-1">
                               <v-btn icon="mdi-pencil" density=default variant=tonal height="32px" width="32px" class="justify-self-center"></v-btn>
                            </v-col>
                        </v-row>
                    </v-container>
                </v-card>
            </v-col>
        </v-row>
    </v-container>

</template>

<script setup lang="ts">
    const partes = ref([
        {nombre: "Juancito pindonga", tipo: "Trabajador", cuit:"20-00000001-0", letri:"Abogado Exitoso", domicilio:"Direccion fulera 123, CABA"},
        {nombre: "Padro cuchuflito guevara lynch", tipo: "Empleador", cuit:"20-00000001-0", letri:"Abogado Exitoso", domicilio:""},
        {nombre: "Juancito pindonga", tipo: "Representante externo", cuit:"20-00000001-0", letri:"El mejor abogado laboralista que el dinero puede conseguir", domicilio:"Direccion fulera 123, CABA"},
        {nombre: "Juancito pindonga", tipo: "Empleador", cuit:"20-00000001-0", letri:"Abogado Exitoso", domicilio:"Yqc"},
    ])
    const letris = ref([
        {nombre: "Abogado exitoso", tf:"123 145", telefono:"11-5432-5131", mail:"letri@mail.com", estudio:"", asig:""}
    ])
    const audiencias = ref([
        {fecha:new Date(2025,0,1,12,0), estado: "Realizada", tipo: "1era", toggleNotif: ref(true), notas:"El abogado de la requerida es un pelotudo, se fija nueva para el cierre"},
        {fecha:new Date(2025,1,14,14,45), estado: "Pendiente", tipo: "Firma", toggleNotif: ref(false), notas:"Puede que haya un acuerdo"}
    ])
    const notifications = ref([
        {nombre: "Juancito Pindonga", emision:new Date(2025, 1, 1), recepcion:new Date(2025,1,10), estado:"00 - Notificad@", tipo:"Telegrama"}
    ])
    const resultados = ref([
        {tipo:"Sin Acuerdo", fecha:new Date(2025,0,1), estado:"Presentado"},
        {tipo:"Sin Acuerdo", fecha:new Date(2025,0,1), estado:"Stand-by"},
        {tipo:"Acuerdo (parcial)", fecha: new Date(2025,0,1), estado:"Aguardando firmas"},
        {tipo:"Acuerdo (parcial-reapertura)", fecha: new Date(2025,0,10), estado: "Borrador"},
        {tipo:"Acuerdo (reapertura)", fecha: new Date(2025,0,10), estado: "Homologado"},
        {tipo:"Acuerdo", fecha: new Date(2025,0,10), estado: "Pagado"},
    ])
    const docs = ref([
        {tipo:"Poder", asoc:"Abogado Exitoso - Empresa multinacional", requerida:true, fecha: null, SECLO:false, subirSECLO:true},
        {tipo:"DNI", asoc:"Juancito Pindonga", requerida:false, fecha: new Date(2025,0,3), SECLO:true, subirSECLO:false},
        {tipo:"Credencial", asoc:"Abogado exitoso", requerida:true, fecha: new Date(2025,0,3), SECLO:false, subirSECLO:false}
    ])

    function toggleNotification(audiencia: any){
        audiencia.toggleNotif = !audiencia.toggleNotif;
        console.log(audiencia.tipo + ' ' + audiencia.toggleNotif);
    }

    function notifMenuIcon(audiencia: any): string{
        return audiencia.toggleNotif ? "mdi-menu-down" : "mdi-menu-right";
    }
</script>

<style lang="sass" scoped>
.expCard
    min-width: 500px
    width:100%
.partesTipo
    max-width: 100%
    min-width: fit-content
.colLimit
    min-width: 120px
.colNoBreak
    overflow: hidden
    white-space: nowrap
.infocol
    overflow: hidden
    text-overflow: ellipsis
    display: -webkit-box
    -webkit-line-clamp: 2
    -webkit-box-orient: vertical
    line-clamp: 2
    word-wrap: normal
</style>