<template>
    <v-card>
        <v-row class="align-center">
            <v-col class="titleColumn ml-2">
                <v-container>
                    <v-row class="titleRow">
                        <img src="@/assets/logo.svg" class="logoImage"/>
                        <v-card-title class="expHeaderTitle">Administracion de expedientes</v-card-title>
                    </v-row>
                </v-container>
            </v-col>
            <v-col>
                <v-container>
                    <v-row>
                        <span>EX-2025-000000001- -APN-DSCLOS#MCH</span>
                    </v-row>
                    <v-row>
                        <span>JUANCITO c/ PINDONGA, CUCHUFLITO Y DIOS SABE QUIEN MAS</span>
                    </v-row>
                </v-container>
            </v-col>
            <v-col>
                <v-container>
                    <v-row>
                        <span>01/01/2025 00:00</span>
                    </v-row>
                    <v-row>
                        <span>RecID 12345678</span>
                    </v-row>
                </v-container>
            </v-col>
        </v-row>
    </v-card>
</template>

<style lang="sass" scoped>
.expHeaderTitle
    word-wrap: normal
    word-break: normal
    white-space: normal
    width: 180px
.logoImage
    object-fit: contain
    height: 64px
    width: 64px
    max-height: 64px
    align-self: center
.titleColumn
    flex-grow: 0
    width: fit-content
.titleRow
    flex-wrap: nowrap
</style>