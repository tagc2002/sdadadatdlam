from datetime import datetime
from decimal import Decimal
from typing import Self


class FEService():
    def __init__(self: Self, token: str, sign: str, cuit: int):
        self.token = token
        self.sign = sign
        self.cuit = cuit

    def FECAESolicitar(self: Self, salePoint: int, invType: int, doctype: int, cuit: int, invoiceDate: datetime, amount: Decimal):
        '''
        Allows generating a CAE validation over at AFIP, to validate an invoice.
        This CAE must be inserted into the actual invoice file.

        Parameters:
            salePoint: sale point associated to the invoice. Must be attained through FEParamGetPtosVenta.
            invType: invoice type associated. Must be attained through FEParamGetTiposCbte.
            cuit: document number of recipient as an int.

        '''
        #docType fixed on 80 (CUIT)
        #concept fixed on 2 (services)
        #cbteDesde y hasta ni la mas puta idea

'''
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soapenv:Header/>
    <soapenv:Body>
        <ar:FECAESolicitar>
            <ar:Auth>
                <ar:Token>string</ar:Token>
                <ar:Sign>string</ar:Sign>
                <ar:Cuit>long</ar:Cuit>
            </ar:Auth>
            <ar:FeCAEReq>
                <ar:FeCabReq>
                    <ar:CantReg>1</ar:CantReg>
                    <ar:PtoVta>int</ar:PtoVta>
                    <ar:CbteTipo>int</ar:CbteTipo>
                </ar:FeCabReq>
                <ar:FeDetReq>
                    <ar:FECAEDetRequest>
                        <ar:Concepto>2</ar:Concepto>
                        <ar:DocTipo>80</ar:DocTipo>
                        <ar:DocNro>long</ar:DocNro>
                        <ar:CbteDesde>long</ar:CbteDesde>
                        <ar:CbteHasta>long</ar:CbteHasta>
                        #<ar:CbteFch>string</ar:CbteFch>
                        <ar:ImpTotal>double</ar:ImpTotal>
                        <ar:ImpTotConc>double</ar:ImpTotConc>
                        <ar:ImpNeto>0</ar:ImpNeto>
                        <ar:ImpOpEx>0</ar:ImpOpEx>
                        <ar:ImpTrib>0</ar:ImpTrib>
                        <ar:ImpIVA>0</ar:ImpIVA>
                        <ar:FchServDesde>string</ar:FchServDesde>
                        <ar:FchServHasta>string</ar:FchServHasta>
                        <ar:FchVtoPago>string</ar:FchVtoPago>
                        <ar:MonId>string</ar:MonId>
                        <ar:MonCotiz>double</ar:MonCotiz>
                        #<ar:CanMisMonExt>string</ar:CanMisMonExt>
                        <ar:CondicionIVAReceptorId>int</ar:CondicionIVAReceptorId>
                        <ar:CbtesAsoc>
                            <ar:CbteAsoc>
                                <ar:Tipo>short</ar:Tipo>
                                <ar:PtoVta>int</ar:PtoVta>
                                <ar:Nro>Long</ar:Nro>
                                <ar:Cuit>String</ar:Cuit>
                                <ar:CbteFch>String</ar:CbteFch>
                            </ar:CbteAsoc>
                        </ar:CbtesAsoc>
                        <ar:Actividades>
                            <ar:Actividad>
                                <ar:Id>Long</ar:Id>
                            </ar:Actividad>
                        </ar:Actividades>
                    </ar:FECAEDetRequest>
                </ar:FeDetReq>
            </ar:FeCAEReq>
        </ar:FECAESolicitar>
    </soapenv:Body>
</soapenv:Envelope>
'''