<template>
    <v-container fluid>
        <v-row class="header-row">
            <v-col class="side-col flex-shrink-0 flex-grow-0"><img src="@/assets/logo.svg" class="logo-image"></v-col>
            <v-col v-for="day in displaydays" class="border header-text" cols="2">
                <v-container>
                    <v-row><span class="header-text">{{ day.name }}</span></v-row>
                    <v-row><span class="header-text">{{ day.date }}</span></v-row>
                </v-container>
            </v-col>
        </v-row>
        <v-row v-for="time in displaytime">
            <v-col class="border flex-shrink-0 flex-grow-0 side-col"><span>{{ time.time }}</span></v-col>
            <v-col v-for="day in displaydays" class="border pa-0 ma-0" cols="2">
                <v-row class="ma-0" cols="1">
                    <v-col class="pa-0 ma-0" >
                        <div v-for="item in items" class="pa-0 ma-0">
                            <v-card v-if="item.time == time.time && item.date == day.date" class=calendarEntry width="100%">
                                <span class="entryLabel">TITULO AUDIENCIA</span>
                            </v-card>
                        </div>
                    </v-col>
                </v-row>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
    const displayweek = Date();
    const items = ref([{ message: 'Foo', date:displayweek, time:"12:00"}, { message: 'Foo', date:1, time:"12:00"},{ message: 'Bar', date:2, time:"13:00"}])
    const displaydays = ref([{date:1, name:"lunes"}, {date:2, name:"martes"}, {date:3, name:"miercoles"}, {date:4, name:"jueves"}, {date:5, name:"viernes"}])
    const displaytime = ref([{time:"12:00"}, {time:"12:30"}, {time:"13:00"}, {time:"13:30"}])
</script>

<style lang="sass" scoped>
.logo-image
    object-fit: contain
    height: 40px
    width: 40px
    max-height: 40px
.header-row
    height: 100%
.header-text
    width: 100%
    text-align: center
.side-col
    height:100%
    width: 64px
.calendarEntry
    background-color: green
.entryLabel
    white-space: nowrap
    word-break: normal
    overflow: hidden
    text-overflow: ellipsis
    width: 100%
</style>