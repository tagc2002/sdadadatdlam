<template>
  <v-app>
    <router-view />
    <button onclick="client.requestCode();">Authorize with Google</button>
  </v-app>
</template>

<script lang="ts" setup>
    // const client = google.accounts.oauth2.initCodeClient({
    //   client_id: '215909080076-jucqip0h570h3uqnv7lj50b2ot5k5em1.apps.googleusercontent.com',
    //   scope: 'https://www.googleapis.com/auth/calendar.readonly',
    //   ux_mode: 'redirect',
    //   redirect_uri: 'http://localhost:8080/api/GoogleTokenAuth',
    //   state: 'YOUR_BINDING_VALUE'
    // });
</script>
