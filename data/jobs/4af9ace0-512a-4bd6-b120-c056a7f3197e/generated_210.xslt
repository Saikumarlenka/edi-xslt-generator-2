<?xml version='1.0' encoding='UTF-8'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp" exclude-result-prefixes="msxsl var s0 userCSharp" version="1.0">

	<xsl:variable name="vLowercaseChars_CONST" select="'abcdefghijklmnopqrstuvwxyz'"/>
	<xsl:variable name="vUppercaseChars_CONST" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"/>

	<xsl:output omit-xml-declaration="yes" method="xml" version="1.0"/>

	<xsl:template match="/">
		<xsl:apply-templates select="/s0:Invoice"/>
	</xsl:template>

	<xsl:template match="/s0:Invoice">
		<ns0:X12_00401_210>
			<ST>
				<ST01>
					<xsl:value-of select="Header/TransactionSetheader/@TransactionSetIdentifierCode"/>
				</ST01>
				<ST02>
					<xsl:value-of select="Header/TransactionSetheader/@TransactionSetControlNumber"/>
				</ST02>

			</ST>

			<ns0:B3>
				<!--segment not mapped by default-->
				<xsl:if test="false()">
					<B301>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@ShipmentQualifier"/>
					</B301>
				</xsl:if>

				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@InvoiceNumber != ''">
					<B302>
						<xsl:call-template name="CleanAlphaField">
							<xsl:with-param name="inputText" select="Header/BeginningSegmentForCarriersInvoice/@InvoiceNumber"/>
							<xsl:with-param name="maxLength" select="22"/>
						</xsl:call-template>
					</B302>
				</xsl:if>
				<xsl:if test="@LoadId != '' ">
					<B303>
						<xsl:call-template name="CleanAlphaField">
							<xsl:with-param name="inputText" select="@LoadId"/>
							<xsl:with-param name="maxLength" select="30"/>
						</xsl:call-template>
					</B303>
				</xsl:if>


				<!--<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@ShipmentMethodOfPayment != '' ">
					<B304>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@ShipmentMethodOfPayment" />
					</B304>
				</xsl:if>-->
				<B304>PP</B304>
				<!--<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@WeightUnitCode != '' ">
					<B305>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@WeightUnitCode" />
					</B305>
				</xsl:if>-->
				<B305>L</B305>
				<xsl:variable name="InvoiceDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='InvoiceDate']"/>
				<xsl:variable name="DeliveryDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='DeliveryDate']"/>
				<xsl:variable name="BillingDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='BillingDate']"/>
				<xsl:variable name="PickupDate" select="//*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@PickupDate"/>
				<xsl:if test="$BillingDate != '' ">
					<B306>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@InvoiceDate"/>
					</B306>
				</xsl:if>
				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@NetAmountDue != '' ">
					<B307>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@NetAmountDue"/>
					</B307>
				</xsl:if>

				<xsl:if test="false()">
					<B308>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@CorrectionIndicator"/>
					</B308>
				</xsl:if>

				<xsl:if test="$DeliveryDate != '' ">
					<B309>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@DeliveryDate"/>
					</B309>
				</xsl:if>
				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@DateTimeQualifier != '' ">
					<B310>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@DateTimeQualifier"/>
					</B310>
				</xsl:if>
				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@StandardCarrierAlphaCode != '' ">
					<B311>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@StandardCarrierAlphaCode"/>
					</B311>
				</xsl:if>
				<xsl:if test="Header/DateTimes/DateTime/@DateQualifier='11'">
					<xsl:if test="$InvoiceDate != '' ">
						<B312>
							<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@PickupDate"/>
						</B312>
					</xsl:if>

				</xsl:if>

				<!--not mapped by default-->
				<xsl:if test="false()">
					<B313>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@TariffServiceCode"/>
					</B313>
				</xsl:if>
				<xsl:if test="false()">
					<B314>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@TransportationTermsCode"/>
					</B314>
				</xsl:if>

			</ns0:B3>
			<!-- Not mapped by default
      <ns0:C2>
        <C201>E</C201>
      </ns0:C2>-->
			<xsl:if test="Header/Currency/@BillingCurrencyCode != '' ">
				<ns0:C3>
					<C301>
						<xsl:value-of select="Header/Currency/@BillingCurrencyCode"/>
					</C301>
				</ns0:C3>
			</xsl:if>
			<xsl:variable name="var:LoadType" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation'][@EDICode = 'LI']/@ReferenceInformation"/>

			<xsl:choose>
				<!-- If Load Type Indicator is not sent or it is not '99', then use the default reference map -->
				<xsl:when test="not(/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation'][@EDICode = 'LI']) or $var:LoadType != '99'">
					<xsl:for-each select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation']">
						<xsl:if test="(@ReferenceInformation != '') or (@EDICode!='') or (@ReferenceInformation!='99')">
							<xsl:choose>
								<xsl:when test="@EDICode='LI' or @EDICode='PO' or @EDICode='DO' or @EDICode='SN' or @EDICode='IL'">
									<ns0:N9>
										<N901>
											<xsl:choose>
												<xsl:when test="@EDICode= 'LI'">T0</xsl:when>
												<xsl:when test="@EDICode= 'SN'">MB</xsl:when>
												<xsl:when test="@EDICode= 'IL'">ZG</xsl:when>
												<xsl:otherwise>
													<xsl:value-of select="@EDICode"/>
												</xsl:otherwise>
											</xsl:choose>
										</N901>
										<N902>
											<xsl:value-of select="@ReferenceInformation"/>
										</N902>
									</ns0:N9>
								</xsl:when>
							</xsl:choose>
						</xsl:if>
					</xsl:for-each>
				</xsl:when>

				<!-- If Load Type Indicator is '99', only show an N9 for PO -->
				<xsl:otherwise>
					<xsl:for-each select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation']">
						<xsl:choose>
							<xsl:when test="@EDICode = 'PO'">
								<ns0:N9>
									<N901>
										<xsl:value-of select="@EDICode"/>
									</N901>
									<N902>
										<xsl:value-of select="@ReferenceInformation"/>
									</N902>
								</ns0:N9>
							</xsl:when>
							<xsl:when test="@EDICode = 'LI'">
								<ns0:N9>
									<N901>
										<xsl:text>T0</xsl:text>
									</N901>
									<N902>
										<xsl:value-of select="@ReferenceInformation"/>
									</N902>
								</ns0:N9>
							</xsl:when>
						</xsl:choose>
					</xsl:for-each>
				</xsl:otherwise>
			</xsl:choose>
			<!--<xsl:variable name="var:LoadType" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation'][@EDICode = 'LI']/@ReferenceInformation"/>			<xsl:for-each select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation']">
				<xsl:if test="(@ReferenceInformation != '') or (@EDICode!='') or (@ReferenceInformation!='99')">
					<xsl:choose>
						<xsl:when test="@EDICode='LI' or @EDICode='PO' or @EDICode='DO' or @EDICode='SN' or @EDICode='IL'">
							<ns0:N9>
								<N901>
									<xsl:choose>
										<xsl:when test="@EDICode= 'LI'">T0</xsl:when>
										<xsl:when test="@EDICode= 'SN'">MB</xsl:when>
										<xsl:when test="@EDICode= 'IL'">ZG</xsl:when>
										<xsl:otherwise>
											<xsl:value-of select="@EDICode" />
										</xsl:otherwise>
									</xsl:choose>
								</N901>
								<N902>
									<xsl:value-of select="@ReferenceInformation" />
								</N902>
							</ns0:N9>
						</xsl:when>
					</xsl:choose>-->


			<!--<ns0:N9>
						<xsl:if test="@EDICode != '' ">
							<N901>
								<xsl:value-of select="@EDICode" />
							</N901>
						</xsl:if>
						<xsl:if test="@ReferenceInformation != '' ">
							<N902>
								<xsl:call-template name="CleanAlphaField" >
									<xsl:with-param name="inputText" select="@ReferenceInformation" />
									<xsl:with-param name="maxLength" select="30" />
								</xsl:call-template>
							</N902>
						</xsl:if>
					</ns0:N9>-->
			<!--</xsl:if>
			</xsl:for-each>-->
			<!-- Not mapped by default-->
			<xsl:variable name="DeliveryDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='DeliveryDate']"/>
			<xsl:variable name="PickupDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='PickupDate']"/>
			<!--<ns0:G62>
				<G6201>11</G6201>
				<G6202>
					<xsl:value-of select="concat(substring($PickupDate, 1, 4), substring($PickupDate, 6, 2), substring($PickupDate, 9, 2))" />
				</G6202>
			</ns0:G62>
			<ns0:G62>
				<G6201>35</G6201>
				<G6202>
					<xsl:value-of select="concat(substring($DeliveryDate, 1, 4), substring($DeliveryDate, 6, 2), substring($DeliveryDate, 9, 2))" />
				</G6202>
			</ns0:G62>-->
			<!--
			<ns0:R3>
				<R301>ECHS</R301>
				<R302>B</R302>
				<R304>M</R304>
				<R306>
					<xsl:value-of select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@InvoiceNumber" />
				</R306>
				<R310>G2</R310>
			</ns0:R3>

			<ns0:K1>
				<xsl:variable name="BMRefInfo" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation'][@EDICode='BM']" />
				<K101>
					<xsl:choose>
						<xsl:when test="$BMRefInfo &gt; ' ' ">
							<xsl:value-of select="$BMRefInfo" /> 
						</xsl:when>
						<xsl:otherwise>
							<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@ShipmentIdentificationNumber" />
						</xsl:otherwise> 
					</xsl:choose> 
				</K101>
			</ns0:K1>-->
			<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode != 'CN' and Name/@EntityIdentifierCode != 'BT' and Name/@EntityIdentifierCode != 'SO']">
				<ns0:N1Loop1>
					<ns0:N1>
						<xsl:choose>
							<xsl:when test="Name/@EntityIdentifierCode = 'SH'">
								<N101>SF</N101>
							</xsl:when>
							<xsl:otherwise>
								<N101>
									<xsl:value-of select="Name/@EntityIdentifierCode"/>
								</N101>
							</xsl:otherwise>
						</xsl:choose>
						<N102>
							<xsl:call-template name="CleanAlphaField">
								<xsl:with-param name="inputText" select="Name/@Name"/>
								<xsl:with-param name="maxLength" select="60"/>
							</xsl:call-template>
						</N102>
						<xsl:choose>
							<xsl:when test="Name/@EntityIdentifierCode = 'SO' and //Header/ReferenceInformation[ReferenceIdentificationQualifier = 'SI']/ReferenceIdentification != ''">
								<N103>93</N103>
								<N104>
									<xsl:value-of select="//Header/ReferenceInformation[ReferenceIdentificationQualifier = 'SI']/ReferenceIdentification"/>
								</N104>
							</xsl:when>
							<xsl:when test="Name/@EntityIdentifierCode = 'SH' and //Header/ReferenceInformation[ReferenceIdentificationQualifier = 'SP']/ReferenceIdentification != ''">
								<N103>93</N103>
								<N104>
									<xsl:value-of select="//Header/ReferenceInformation[ReferenceIdentificationQualifier = 'SP']/ReferenceIdentification"/>
								</N104>
							</xsl:when>
						</xsl:choose>
					</ns0:N1>
					<xsl:if test="AddressInformation/@AddressInformationLine1 != '' or AddressInformation/@AddressInformationLine2 != ''">
						<ns0:N3>
							<xsl:if test="AddressInformation/@AddressInformationLine1 != ''">
								<N301>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine1"/>
										<xsl:with-param name="maxLength" select="55"/>
									</xsl:call-template>
								</N301>
							</xsl:if>
							<!--<xsl:if test="AddressInformation/@AddressInformationLine2 != ''">
								<N302>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine2" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N302>
							</xsl:if>-->
						</ns0:N3>
					</xsl:if>
					<xsl:if test="GeographicLocation/@CityName != '' or GeographicLocation/@StateOrProvinceCode != '' or GeographicLocation/@PostalCode != ''">
						<ns0:N4>
							<xsl:if test="GeographicLocation/@CityName != ''">
								<N401>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="GeographicLocation/@CityName"/>
										<xsl:with-param name="maxLength" select="55"/>
									</xsl:call-template>
								</N401>
							</xsl:if>
							<xsl:if test="GeographicLocation/@StateOrProvinceCode != ''">
								<N402>
									<xsl:value-of select="GeographicLocation/@StateOrProvinceCode"/>
								</N402>
							</xsl:if>
							<xsl:if test="GeographicLocation/@PostalCode != ''">
								<N403>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="GeographicLocation/@PostalCode"/>
										<xsl:with-param name="maxLength" select="55"/>
									</xsl:call-template>
								</N403>
							</xsl:if>
							<xsl:if test="GeographicLocation/@CountryCode != ''">
								<N404>
									<xsl:value-of select="GeographicLocation/@CountryCode"/>
								</N404>
							</xsl:if>
						</ns0:N4>
					</xsl:if>
				</ns0:N1Loop1>
			</xsl:for-each>
			<xsl:if test="Header/PartyList/Party/Name/@EntityIdentifierCode='SO' and Header/PartyList/Party/Name/@Name!=''">
				<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode='SO']">
					<ns0:N1Loop1>
						<ns0:N1>
							<N101>
								<xsl:value-of select="Name/@EntityIdentifierCode"/>
							</N101>
							<N102>
								<xsl:call-template name="CleanAlphaField">
									<xsl:with-param name="inputText" select="Name/@Name"/>
									<xsl:with-param name="maxLength" select="60"/>
								</xsl:call-template>
							</N102>
						</ns0:N1>
						<xsl:if test="(AddressInformation/@AddressInformationLine1 != '') or (AddressInformation/@AddressInformationLine2 != '') ">
							<ns0:N3>
								<xsl:if test="AddressInformation/@AddressInformationLine1 != ''">
									<N301>
										<xsl:call-template name="CleanAlphaField">
											<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine1"/>
											<xsl:with-param name="maxLength" select="55"/>
										</xsl:call-template>
									</N301>
								</xsl:if>
								<!--<xsl:if test="AddressInformation/@AddressInformationLine2 != ''">
								<N302>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine2" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N302>
							</xsl:if>-->
							</ns0:N3>
						</xsl:if>
						<xsl:if test="(GeographicLocation/@CityName != '') or (GeographicLocation/@StateOrProvinceCode != '') or (GeographicLocation/@PostalCode != '')">
							<ns0:N4>
								<xsl:if test="GeographicLocation/@CityName != ''">
									<N401>
										<xsl:call-template name="CleanAlphaField">
											<xsl:with-param name="inputText" select="GeographicLocation/@CityName"/>
											<xsl:with-param name="maxLength" select="55"/>
										</xsl:call-template>
									</N401>
								</xsl:if>
								<xsl:if test="GeographicLocation/@StateOrProvinceCode != ''">
									<N402>
										<xsl:value-of select="GeographicLocation/@StateOrProvinceCode"/>
									</N402>
								</xsl:if>
								<xsl:if test="GeographicLocation/@PostalCode != ''">
									<N403>
										<xsl:call-template name="CleanAlphaField">
											<xsl:with-param name="inputText" select="GeographicLocation/@PostalCode"/>
											<xsl:with-param name="maxLength" select="55"/>
										</xsl:call-template>
									</N403>
								</xsl:if>
								<xsl:if test="GeographicLocation/@CountryCode != ''">
									<N404>
										<xsl:value-of select="GeographicLocation/@CountryCode"/>
									</N404>
								</xsl:if>
							</ns0:N4>
						</xsl:if>
					</ns0:N1Loop1>
				</xsl:for-each>

			</xsl:if>



			<!--<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode='BT']">
				<ns0:N1Loop1>
					<ns0:N1>
						<N101>
							<xsl:value-of select="Name/@EntityIdentifierCode" />
						</N101>
						<N102>
							<xsl:call-template name="CleanAlphaField" >
								<xsl:with-param name="inputText" select="Name/@Name" />
								<xsl:with-param name="maxLength" select="60" />
							</xsl:call-template>
						</N102>
					</ns0:N1>
					<xsl:if test="(AddressInformation/@AddressInformationLine1 != '') or (AddressInformation/@AddressInformationLine2 != '') ">
						<ns0:N3>
							<xsl:if test="AddressInformation/@AddressInformationLine1 != ''">
								<N301>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine1" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N301>
							</xsl:if>
							<xsl:if test="AddressInformation/@AddressInformationLine2 != ''">
								<N302>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine2" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N302>
							</xsl:if>
						</ns0:N3>
					</xsl:if>
					<xsl:if test="(GeographicLocation/@CityName != '') or (GeographicLocation/@StateOrProvinceCode != '') or (GeographicLocation/@PostalCode != '')">
						<ns0:N4>
							<xsl:if test="GeographicLocation/@CityName != ''">
								<N401>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="GeographicLocation/@CityName" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N401>
							</xsl:if>
							<xsl:if test="GeographicLocation/@StateOrProvinceCode != ''">
								<N402>
									<xsl:value-of select="GeographicLocation/@StateOrProvinceCode" />
								</N402>
							</xsl:if>
							<xsl:if test="GeographicLocation/@PostalCode != ''">
								<N403>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="GeographicLocation/@PostalCode" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N403>
							</xsl:if>
							<xsl:if test="GeographicLocation/@CountryCode != ''">
								<N404>
									<xsl:value-of select="GeographicLocation/@CountryCode" />
								</N404>
							</xsl:if>
						</ns0:N4>
					</xsl:if>
				</ns0:N1Loop1>
			</xsl:for-each>-->

			<!--Template not used for a code below due to expected changes to mappings from one code to another-->
			<!--<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode='SH'][1]">
				<ns0:N1Loop1>
					<ns0:N1>
						<N101>
							<xsl:value-of select="Name/@EntityIdentifierCode" />
						</N101>
						<N102>
							<xsl:call-template name="CleanAlphaField" >
								<xsl:with-param name="inputText" select="Name/@Name" />
								<xsl:with-param name="maxLength" select="60" />
							</xsl:call-template>
						</N102>
					</ns0:N1>
					<xsl:if test="(AddressInformation/@AddressInformationLine1 != '') or (AddressInformation/@AddressInformationLine2 != '') ">
						<ns0:N3>
							<xsl:if test="AddressInformation/@AddressInformationLine1 != ''">
								<N301>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine1" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N301>
							</xsl:if>
							<xsl:if test="AddressInformation/@AddressInformationLine2 != ''">
								<N302>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine2" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N302>
							</xsl:if>
						</ns0:N3>
					</xsl:if>
					<xsl:if test="(GeographicLocation/@CityName != '') or (GeographicLocation/@StateOrProvinceCode != '') or (GeographicLocation/@PostalCode != '')">
						<ns0:N4>
							<xsl:if test="GeographicLocation/@CityName != ''">
								<N401>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="GeographicLocation/@CityName" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N401>
							</xsl:if>
							<xsl:if test="GeographicLocation/@StateOrProvinceCode != ''">
								<N402>
									<xsl:value-of select="GeographicLocation/@StateOrProvinceCode" />
								</N402>
							</xsl:if>
							<xsl:if test="GeographicLocation/@PostalCode != ''">
								<N403>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="GeographicLocation/@PostalCode" />
										<xsl:with-param name="maxLength" select="55" />
									</xsl:call-template>
								</N403>
							</xsl:if>
							<xsl:if test="GeographicLocation/@CountryCode != ''">
								<N404>
									<xsl:value-of select="GeographicLocation/@CountryCode" />
								</N404>
							</xsl:if>
						</ns0:N4>
					</xsl:if>
				</ns0:N1Loop1>
			</xsl:for-each>-->

			<!--Template not used for a code below due to expected changes to mappings from one code to another-->
			<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode='CN']">
				<xsl:if test="position() = last()">
					<ns0:N1Loop1>
						<ns0:N1>
							<N101>ST</N101>
							<N102>
								<xsl:call-template name="CleanAlphaField">
									<xsl:with-param name="inputText" select="Name/@Name"/>
									<xsl:with-param name="maxLength" select="60"/>
								</xsl:call-template>
							</N102>
						</ns0:N1>
						<xsl:if test="(AddressInformation/@AddressInformationLine1 != '') or (AddressInformation/@AddressInformationLine2 != '') ">
							<ns0:N3>
								<xsl:if test="AddressInformation/@AddressInformationLine1 != ''">
									<N301>
										<xsl:call-template name="CleanAlphaField">
											<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine1"/>
											<xsl:with-param name="maxLength" select="55"/>
										</xsl:call-template>
									</N301>
								</xsl:if>
								<!--<xsl:if test="AddressInformation/@AddressInformationLine2 != ''">
									<N302>
										<xsl:call-template name="CleanAlphaField" >
											<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine2" />
											<xsl:with-param name="maxLength" select="55" />
										</xsl:call-template>
									</N302>
								</xsl:if>-->
							</ns0:N3>
						</xsl:if>
						<xsl:if test="(GeographicLocation/@CityName != '') or (GeographicLocation/@StateOrProvinceCode != '') or (GeographicLocation/@PostalCode != '')">
							<ns0:N4>
								<xsl:if test="GeographicLocation/@CityName != ''">
									<N401>
										<xsl:call-template name="CleanAlphaField">
											<xsl:with-param name="inputText" select="GeographicLocation/@CityName"/>
											<xsl:with-param name="maxLength" select="55"/>
										</xsl:call-template>
									</N401>
								</xsl:if>
								<xsl:if test="GeographicLocation/@StateOrProvinceCode != ''">
									<N402>
										<xsl:value-of select="GeographicLocation/@StateOrProvinceCode"/>
									</N402>
								</xsl:if>
								<xsl:if test="GeographicLocation/@PostalCode != ''">
									<N403>
										<xsl:call-template name="CleanAlphaField">
											<xsl:with-param name="inputText" select="GeographicLocation/@PostalCode"/>
											<xsl:with-param name="maxLength" select="55"/>
										</xsl:call-template>
									</N403>
								</xsl:if>
								<xsl:if test="GeographicLocation/@CountryCode != ''">
									<N404>
										<xsl:value-of select="GeographicLocation/@CountryCode"/>
									</N404>
								</xsl:if>
							</ns0:N4>
						</xsl:if>
					</ns0:N1Loop1>

				</xsl:if>

			</xsl:for-each>
			<xsl:variable name="NumberOfN7" select="count (Header/EquipmentList/Equipment[@EquipmentNumber != ''])"/>
			<!--<xsl:if test="$NumberOfN7 > 0">
				<ns0:N7Loop1>
					<xsl:for-each select="Header/EquipmentList/Equipment">
						<ns0:N7>
							<xsl:if test="@EquipmentNumber != ''">
								<N702>
									<xsl:value-of select="@EquipmentNumber" />
								</N702>
							</xsl:if>
							<xsl:if test="@EquipmentDescriptionCode != ''">
								<N711>
									<xsl:value-of select="@EquipmentDescriptionCode" />
								</N711>
							</xsl:if>
							<xsl:if test="@EquipmentDescriptionCode != ''">
								<N715>
									<xsl:value-of select="@EquipmentLength" />
								</N715>
							</xsl:if>
						</ns0:N7>
					</xsl:for-each>
				</ns0:N7Loop1>
			</xsl:if>-->
			<!--Create S5Loop1 only for last recored where party Identifier Codes is 'CN',-->
			<xsl:variable name="NumberOfParties" select="count (Header/PartyList/Party)"/>

			<!--<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode='CN']">
      
			<xsl:for-each select="Header/PartyList/Party">-->
			<!--
        <xsl:if test="position() &lt; $NumberOfParties">
				<ns0:S5Loop1>
						<ns0:S5>
							<S501>
								<xsl:value-of select="position()" />
							</S501>
							<S502>PU</S502>
              <xsl:if test="../../../Summary/TotalWeightAndCharges/@Weight">
              <S503>
                <xsl:value-of select="../../../Summary/TotalWeightAndCharges/@Weight" />
              </S503>
              <S504>L</S504>
              </xsl:if>
						</ns0:S5>
           <xsl:for-each select="../../ReferenceList/ReferenceInformation">
            <xsl:if test="(@ReferenceInformationQualifier != '') or (@ReferenceInformation != '') ">
              <ns0:N9_3>
                <xsl:if test="@EDICode != '' ">
                  <N901>
                    <xsl:value-of select="@EDICode" />
                  </N901>
                </xsl:if>
                <xsl:if test="@ReferenceInformation != '' ">
                  <N902>
                    <xsl:call-template name="CleanAlphaField" >
                      <xsl:with-param name="inputText" select="@ReferenceInformation" />
                      <xsl:with-param name="maxLength" select="30" />
                    </xsl:call-template>
                  </N902>
                </xsl:if>
              </ns0:N9_3>
            </xsl:if>
          </xsl:for-each>
				</ns0:S5Loop1>
        </xsl:if>
			</xsl:for-each>-->

			<!--<xsl:variable name="CountofSH" select="count(PartyList/Party[Name/@EntityIdentifierCode='SH'][1]) - 1" /> 


			<xsl:for-each select="PartyList/Party[Name/@EntityIdentifierCode='CN']">
				<xsl:variable name="PositionOfCN" select="position()" />
				<ns0:S5Loop1>
					<xsl:if test="$PositionOfCN != last()">
						<ns0:S5>
							<S501>
								<xsl:value-of select="$CountofSH + position()" />
							</S501>
							<S502>CU</S502>
						</ns0:S5>
						<ns0:N1Loop2>
							<ns0:N1_2>
								<N101>
									<xsl:value-of select="Name/@EntityIdentifierCode" />
								</N101>
								<N102>
									<xsl:value-of select="Name/@Name" />
								</N102>
							</ns0:N1_2>
							<ns0:N3_2>
								<N301>
									<xsl:value-of select="AddressInformation/@AddressInformationLine1" />
								</N301>
							</ns0:N3_2>
							<ns0:N4_2>
								<xsl:if test="GeographicLocation/@CityName != '' ">
									<N401>
										<xsl:value-of select="GeographicLocation/@CityName" />
									</N401>
								</xsl:if>
								<xsl:if test="GeographicLocation/@StateOrProvinceCode != '' ">
									<N402>
										<xsl:value-of select="GeographicLocation/@StateOrProvinceCode" />
									</N402>
								</xsl:if>
								<xsl:if test="GeographicLocation/@PostalCode != '' ">
									<N403>
										<xsl:value-of select="GeographicLocation/@PostalCode" />
									</N403>
								</xsl:if>
								<xsl:if test="GeographicLocation/@CountryCode != '' ">
									<N404>
										<xsl:value-of select="GeographicLocation/@CountryCode" />
									</N404>
								</xsl:if>
							</ns0:N4_2>
						</ns0:N1Loop2>
					</xsl:if>
				</ns0:S5Loop1>
			</xsl:for-each>-->
			<xsl:for-each select="Detail/StopList">
				<xsl:for-each select="StopOffDetails">
					<xsl:variable name="var:v20" select="userCSharp:LogicalEq(string(@StopReasonCode) , &quot;Pick&quot;)"/>
					<xsl:variable name="var:v23" select="string(@PickStopNo)"/>
					<xsl:variable name="var:v27" select="string(@StopReasonCode)"/>
					<xsl:variable name="var:v28" select="userCSharp:LogicalEq($var:v27 , &quot;Drop&quot;)"/>
					<xsl:variable name="var:v35" select="string(@DropStopNo)"/>
					<xsl:variable name="var:v39" select="userCSharp:LogicalEq($var:v27 , &quot;Pick&quot;)"/>
					<ns0:S5Loop1>
						<ns0:S5>
							<S501>
								<xsl:value-of select="@StopSequenceNumber"/>
							</S501>
							<xsl:variable name="var:v16" select="userCSharp:InitCumulativeMax(0)"/>
							<xsl:for-each select="../StopOffDetails">
								<xsl:variable name="var:v17" select="userCSharp:AddToCumulativeMax(0,string(@PickStopNo),&quot;1&quot;)"/>
							</xsl:for-each>
							<xsl:variable name="var:v18" select="userCSharp:GetCumulativeMax(0)"/>
							<xsl:variable name="var:v19" select="userCSharp:LogicalEq(string($var:v18) , string(@PickStopNo))"/>
							<xsl:variable name="var:v21" select="userCSharp:LogicalAnd(string($var:v19) , string($var:v20))"/>
							<xsl:if test="string($var:v21)='true'">
								<S502>CL</S502>
							</xsl:if>
							<xsl:variable name="var:v24" select="userCSharp:LogicalNe(string($var:v18) , $var:v23)"/>
							<xsl:variable name="var:v25" select="userCSharp:LogicalAnd(string($var:v20) , string($var:v24))"/>
							<xsl:if test="string($var:v25)='true'">
								<S502>PL</S502>
							</xsl:if>
							<xsl:variable name="var:v29" select="userCSharp:InitCumulativeMax(1)"/>
							<xsl:for-each select="../StopOffDetails">
								<xsl:variable name="var:v30" select="userCSharp:AddToCumulativeMax(1,string(@DropStopNo),&quot;1&quot;)"/>
							</xsl:for-each>
							<xsl:variable name="var:v31" select="userCSharp:GetCumulativeMax(1)"/>
							<xsl:variable name="var:v32" select="userCSharp:LogicalEq(string($var:v31) , string(@DropStopNo))"/>
							<xsl:variable name="var:v33" select="userCSharp:LogicalAnd(string($var:v28) , string($var:v32))"/>
							<xsl:if test="string($var:v33)='true'">
								<xsl:variable name="var:v34" select="&quot;CU&quot;"/>
								<S502>CU</S502>
							</xsl:if>
							<xsl:variable name="var:v36" select="userCSharp:LogicalNe(string($var:v31) , $var:v35)"/>
							<xsl:variable name="var:v37" select="userCSharp:LogicalAnd(string($var:v28) , string($var:v36))"/>
							<xsl:if test="string($var:v37)='true'">
								<S502>PU</S502>
							</xsl:if>
						</ns0:S5>
						<ns0:N1Loop2>
							<ns0:N1_2>
								<xsl:if test="string($var:v39)='true'">
									<N101>SF</N101>
								</xsl:if>
								<xsl:if test="string($var:v28)='true'">
									<N101>ST</N101>
								</xsl:if>
								<xsl:if test="NameAddressInformation/@Name != ''">
									<N102>
										<xsl:value-of select="NameAddressInformation/@Name"/>
									</N102>
								</xsl:if>
							</ns0:N1_2>
							<ns0:N3_2>
								<xsl:if test="NameAddressInformation/@AddressLine1 != ''">
									<N301>
										<xsl:value-of select="NameAddressInformation/@AddressLine1"/>
									</N301>
								</xsl:if>
							</ns0:N3_2>
							<ns0:N4_2>
								<xsl:if test="GeographicalInformation/@CityName != ''">
									<N401>
										<xsl:value-of select="GeographicalInformation/@CityName"/>
									</N401>
								</xsl:if>
								<xsl:if test="GeographicalInformation/@StateOrProvinceCode != ''">
									<N402>
										<xsl:value-of select="GeographicalInformation/@StateOrProvinceCode"/>
									</N402>
								</xsl:if>
								<xsl:if test="GeographicalInformation/@PostalCode != ''">
									<N403>
										<xsl:value-of select="GeographicalInformation/@PostalCode"/>
									</N403>
								</xsl:if>
								<xsl:if test="GeographicalInformation/@CountryCode != ''">
									<N404>
										<xsl:value-of select="GeographicalInformation/@CountryCode"/>
									</N404>
								</xsl:if>
							</ns0:N4_2>
						</ns0:N1Loop2>
					</ns0:S5Loop1>
				</xsl:for-each>
			</xsl:for-each>

			<xsl:for-each select="Detail/LineItemList/LineItem">
				<!--<xsl:variable name="countof" select="count(RateAndCharges/@RateCombinationPointCode)"></xsl:variable>-->

				<ns0:LXLoop1>
					<ns0:LX>
						<LX01>
							<xsl:value-of select="AssignedNumber/@AssignedNumber"/>
						</LX01>
					</ns0:LX>
					<xsl:if test="//Header/ReferenceList/ReferenceInformation/@EDICode='HU'">
						<ns0:N9_5>
							<N901>QQ</N901>
							<N902>
								<xsl:value-of select="//Header/ReferenceList/ReferenceInformation/@ReferenceInformation"/>
							</N902>
						</ns0:N9_5>
					</xsl:if>

					<ns0:L5>
						<xsl:if test="DescriptionMarksAndNumbers/@LadingLineItemNumber != ''">
							<L501>
								<xsl:value-of select="DescriptionMarksAndNumbers/@LadingLineItemNumber"/>
							</L501>
						</xsl:if>
						<xsl:if test="DescriptionMarksAndNumbers/@LadingDescription != ''">
							<L502>
								<!-- Convert to UpperCase <xsl:value-of select="translate(DescriptionMarksAndNumbers/@LadingDescription,  $vLowercaseChars_CONST, $vUppercaseChars_CONST)" />-->
								<xsl:call-template name="CleanAlphaField">
									<xsl:with-param name="inputText" select="DescriptionMarksAndNumbers/@LadingDescription"/>
									<xsl:with-param name="maxLength" select="50"/>
								</xsl:call-template>
							</L502>
						</xsl:if>
					</ns0:L5>
					<xsl:if test="LineItemQuantityAndWeight/@LadingQuantity!=0 and count(RateAndCharges/@RateCombinationPointCode) = 0">
						<ns0:L0>
							<xsl:if test="DescriptionMarksAndNumbers/@LadingLineItemNumber != ''">
								<L001>
									<xsl:value-of select="DescriptionMarksAndNumbers/@LadingLineItemNumber"/>
								</L001>
							</xsl:if>
							<xsl:if test="LineItemQuantityAndWeight/@LadingQuantity != ''">
								<L002>
									<xsl:value-of select="LineItemQuantityAndWeight/LineItemQuantityAndWeight/@BilledRatedAsQuantity"/>
								</L002>
							</xsl:if>
							<!--<xsl:if test="LineItemQuantityAndWeight/@BilledRatedAsQualifier != ''">
							<L003>
								<xsl:value-of select="LineItemQuantityAndWeight/@BilledRatedAsQualifier" />
							</L003>
						</xsl:if>-->
							<L003>FR</L003>
							<xsl:if test="LineItemQuantityAndWeight/@Weight != ''">
								<L004>
									<xsl:value-of select="LineItemQuantityAndWeight/TotalWeightAndCharges/@Weight"/>
								</L004>
								<L005>
									<xsl:value-of select="'L'"/>
								</L005>
							</xsl:if>
							<!--<xsl:if test="LineItemQuantityAndWeight/@LadingQuantity != ''">
							<L007>
								<xsl:value-of select="LineItemQuantityAndWeight/@LadingQuantity" />
							</L007>
						</xsl:if>-->

							<xsl:if test="LineItemQuantityAndWeight/@LadingQuantity != ''">
								<L008>
									<xsl:value-of select="LineItemQuantityAndWeight/TotalWeightAndCharges//@LadingQuantity"/>
								</L008>
							</xsl:if>
							<xsl:if test="LineItemQuantityAndWeight/@LadingQuantityPackagingFormCode != ''">
								<L009>
									<xsl:value-of select="'PLT'"/>
								</L009>
							</xsl:if>
							<!--<xsl:if test="LineItemQuantityAndWeight/@WeightUnitCode != ''">
							<L011>
								<xsl:value-of select="LineItemQuantityAndWeight/@WeightUnitCode" />
							</L011>
						</xsl:if>-->
						</ns0:L0>

					</xsl:if>


					<xsl:if test="count(RateAndCharges/@FreightRate) &gt; 0 or RateAndCharges/@FreightRate != '' or RateAndCharges/@Charge != '' or RateAndCharges/@SpecialChargeOrAllowanceCode != ''">
						<ns0:L1>
							<L101>
								<xsl:value-of select="position()"/>
							</L101>
							<xsl:choose>
								<xsl:when test="contains(RateAndCharges/@FreightRate, '.') and string-length(substring-after(RateAndCharges/@FreightRate, '.')) = 2">
									<L102>
										<xsl:value-of select="RateAndCharges/@FreightRate"/>
									</L102>
									<L103>
										<xsl:value-of select="RateAndCharges/@RateValueQualifier"/>
									</L103>
									<L104>
										<xsl:value-of select="translate(RateAndCharges/@Charge,'.','')"/>
									</L104>
								</xsl:when>
								<xsl:when test="contains(RateAndCharges/@FreightRate, '.') and string-length(substring-after(RateAndCharges/@FreightRate, '.')) = 1">
									<L102>
										<xsl:value-of select="concat(RateAndCharges/@FreightRate, '0')"/>
									</L102>
									<L103>
										<xsl:value-of select="RateAndCharges/@RateValueQualifier"/>
									</L103>
									<L104>
										<xsl:value-of select="RateAndCharges/@Charge"/>
									</L104>
								</xsl:when>
								<xsl:otherwise>
									<L102>
										<xsl:value-of select="concat(RateAndCharges/@FreightRate, '.00')"/>
									</L102>
									<L103>
										<xsl:value-of select="RateAndCharges/@RateValueQualifier"/>
									</L103>
									<L104>
										<xsl:value-of select="concat(RateAndCharges/@Charge, '00')"/>
									</L104>
								</xsl:otherwise>
							</xsl:choose>
							<!--<xsl:if test="RateAndCharges/@FreightRate != ''">
								<L102>
									-->
							<!--<xsl:value-of select="format-number(RateAndCharges/@FreightRate, '#')" />-->
							<!--
									<xsl:value-of select="RateAndCharges/@FreightRate" />
								</L102>
							</xsl:if>
							<xsl:if test="RateAndCharges/@RateValueQualifier != ''">
								<L103>
									<xsl:value-of select="RateAndCharges/@RateValueQualifier" />
								</L103>
							</xsl:if>
							<xsl:if test="RateAndCharges/@Charge != ''">
								<L104>
									<xsl:value-of select="RateAndCharges/@Charge" />
								</L104>
							</xsl:if>-->
							<!--L107 not mapped by default-->

							<xsl:if test="false()">
								<L107>
									<xsl:value-of select="RateAndCharges/@RateCombinationPointCode"/>
								</L107>
							</xsl:if>

							<xsl:if test="false()">
								<L108>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="RateAndCharges/@SpecialChargeOrAllowanceCode"/>
										<xsl:with-param name="maxLength" select="9"/>
									</xsl:call-template>
								</L108>
							</xsl:if>
							<!--<xsl:if test="RateAndCharges/@SpecialChargeDescription != ''">
              <L112>
                <xsl:call-template name="CleanAlphaField" >
                  <xsl:with-param name="inputText" select="RateAndCharges/@SpecialChargeDescription" />
                  <xsl:with-param name="maxLength" select="25" />
                </xsl:call-template>
              </L112>
            </xsl:if>-->
						</ns0:L1>
					</xsl:if>
				</ns0:LXLoop1>
			</xsl:for-each>

			<xsl:for-each select="Summary/TotalWeightAndCharges">
				<ns0:L3>
					<xsl:if test="@Weight">
						<L301>
							<xsl:value-of select="TotalWeightAndCharges/@Weight"/>
						</L301>
					</xsl:if>
					<xsl:if test="@WeightQualifier">
						<L302>G</L302>
					</xsl:if>
					<xsl:variable name="TotalCharges" select="@TotalCharges"/>
					<xsl:variable name="TotalChargesLength" select="string-length(@TotalCharges)"/>
					<xsl:if test="$TotalChargesLength &gt; 2">
						<L305>
							<xsl:value-of select="TotalWeightAndCharges/@TotalCharges"/>
							<!--<xsl:value-of select="concat(substring($TotalCharges, 1, $TotalChargesLength - 2), '.',  substring($TotalCharges, $TotalChargesLength - 2 , 2))" />-->
						</L305>
					</xsl:if>
					<xsl:if test="@LadingQuantity">
						<L311>
							<xsl:value-of select="TotalWeightAndCharges/@LadingQuantity"/>
						</L311>
					</xsl:if>
				</ns0:L3>
			</xsl:for-each>
			<SE>
				<SE01>
					<xsl:value-of select="Header/TransactionSetheader/@TransactionSetIdentifierCode"/>
				</SE01>
				<SE02>
					<xsl:value-of select="Header/TransactionSetheader/@TransactionSetControlNumber"/>
				</SE02>
			</SE>
		</ns0:X12_00401_210>
	</xsl:template>

	<!--Custom Templates-->

	<!-- Created by Neal, not specific to L108-->
	<xsl:template name="ChangeThisName">
		<xsl:param name="ValueToConvert" select="0"/>
		<xsl:param name="LadingDescriptionParm" select="1"/>
		<xsl:variable name="L108Map">
			<map>
				<entry key="LHS">400</entry>
				<entry key="LYC">LAY</entry>
				<entry key="SRG">STR</entry>
				<entry key="TDT">DET</entry>
			</map>
		</xsl:variable>
		<xsl:variable name="ValueConverted" select="msxsl:node-set($L108Map)/map/entry[@key=$ValueToConvert]"/>
		<xsl:choose>
			<xsl:when test="$ValueConverted">
				<xsl:value-of select="$ValueConverted"/>
			</xsl:when>
			<xsl:otherwise>
				<xsl:choose>
					<xsl:when test="$LadingDescriptionParm = 'Lumper'">
						<xsl:text>LAB</xsl:text>
					</xsl:when>
					<xsl:when test="$LadingDescriptionParm = 'Unloading'">
						<xsl:text>UNL</xsl:text>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="$ValueToConvert"/>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>
	<!-- Created by Neal, not specific to L108-->

	<!-- CleanAlphaField start  -->
	<xsl:template name="CleanAlphaField">
		<xsl:param name="inputText"/>
		<xsl:param name="maxLength"/>
		<xsl:variable name="singleQuote" select="&quot;'&quot;"/>
		<xsl:variable name="doubleQuote" select="'&quot;'"/>
		<xsl:variable name="vAllowedSymbolsPart1" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890 !@$%()+-_,.;=[]{}\?/#'"/>
		<xsl:variable name="vAllowedSymbols" select="concat($vAllowedSymbolsPart1, $singleQuote, $doubleQuote)"/>
		<xsl:variable name="vCleanedText" select="translate($inputText,translate($inputText, $vAllowedSymbols, ''),'')"/>
		<xsl:value-of select="substring(normalize-space($vCleanedText), 1, $maxLength)"/>
	</xsl:template>
	<!-- Clean AlphaField end -->

	<!--Value mapping template-->
	<xsl:template name="StopTypeMapValue">
		<xsl:param name="ValueToConvert" select="0"/>
		<xsl:variable name="StopTypeMap">
			<map>
				<entry key="Pick">SF</entry>
				<entry key="Drop">CN</entry>
			</map>
		</xsl:variable>
		<xsl:value-of select="msxsl:node-set($StopTypeMap)/map/entry[@key=$ValueToConvert]"/>
	</xsl:template>
	<!--Value mapping template-->

	<!--Set default if empty template start-->
	<xsl:template name="SetDefaultIfEmpty">
		<xsl:param name="pNode"/>
		<xsl:param name="pDefaultValue"/>
		<xsl:if test="$pNode">
			<xsl:value-of select="$pNode"/>
		</xsl:if>
		<xsl:if test="not($pNode)">
			<xsl:value-of select="$pDefaultValue"/>
		</xsl:if>
	</xsl:template>
	<!--Set default if empty template end-->
	<msxsl:script language="C#" implements-prefix="userCSharp">
		

public string FormatEDIInvoiceDate(string param1)
{
	string year = param1.Substring(0,4); 
                string month = param1.Substring(5,2); 
                string day = param1.Substring(8,2); 
                return year + month + day; 
}



public string FormatEDDeliveryDate(string param1)
{
	string year = param1.Substring(0,4); 
                string month = param1.Substring(5,2); 
                string day = param1.Substring(8,2); 
                return year + month + day; 
}



public string FormatEDIBillingDate(string param1)
{
	string year = param1.Substring(0,4); 
                string month = param1.Substring(5,2); 
                string day = param1.Substring(8,2); 
                return year + month + day; 
}


public string StringConcat(string param0)
{
   return param0;
}


public bool LogicalEq(string val1, string val2)
{
	bool ret = false;
	double d1 = 0;
	double d2 = 0;
	if (IsNumeric(val1, ref d1) &amp;&amp; IsNumeric(val2, ref d2))
	{
		ret = d1 == d2;
	}
	else
	{
		ret = String.Compare(val1, val2, StringComparison.Ordinal) == 0;
	}
	return ret;
}


public bool LogicalNot(string val)
{
	return !ValToBool(val);
}


public bool LogicalAnd(string param0, string param1)
{
	return ValToBool(param0) &amp;&amp; ValToBool(param1);
	return false;
}


public bool LogicalExistence(bool val)
{
	return val;
}


public bool LogicalGt(string val1, string val2)
{
	bool ret = false;
	double d1 = 0;
	double d2 = 0;
	if (IsNumeric(val1, ref d1) &amp;&amp; IsNumeric(val2, ref d2))
	{
		ret = d1 &gt; d2;
	}
	else
	{
		ret = String.Compare(val1, val2, StringComparison.Ordinal) &gt; 0;
	}
	return ret;
}


public string InitCumulativeMax(int index)
{
	if (index &gt;= 0)
	{
		if (index &gt;= myCumulativeMaxArray.Count)
		{
			int i = myCumulativeMaxArray.Count;
			for (; i&lt;=index; i++)
			{
				myCumulativeMaxArray.Add("");
			}
		}
		else
		{
			myCumulativeMaxArray[index] = "";
		}
	}
	return "";
}

public System.Collections.ArrayList myCumulativeMaxArray = new System.Collections.ArrayList();

public string AddToCumulativeMax(int index, string val, string notused)
{
	if (index &lt; 0 || index &gt;= myCumulativeMaxArray.Count)
	{
		return "";
	}
	double d = 0;
	if (IsNumeric(val, ref d))
	{
		if (myCumulativeMaxArray[index] is string || (d &gt; (double)(myCumulativeMaxArray[index])))
		{
			myCumulativeMaxArray[index] = d;
		}
	}
	return (myCumulativeMaxArray[index] is double) ? ((double)myCumulativeMaxArray[index]).ToString(System.Globalization.CultureInfo.InvariantCulture) : "";
}

public string GetCumulativeMax(int index)
{
	if (index &lt; 0 || index &gt;= myCumulativeMaxArray.Count)
	{
		return "";
	}
	return (myCumulativeMaxArray[index] is double) ? ((double)myCumulativeMaxArray[index]).ToString(System.Globalization.CultureInfo.InvariantCulture) : "";
}

public bool LogicalNe(string val1, string val2)
{
	bool ret = false;
	double d1 = 0;
	double d2 = 0;
	if (IsNumeric(val1, ref d1) &amp;&amp; IsNumeric(val2, ref d2))
	{
		ret = d1 != d2;
	}
	else
	{
		ret = String.Compare(val1, val2, StringComparison.Ordinal) != 0;
	}
	return ret;
}


public bool IsNumeric(string val)
{
	if (val == null)
	{
		return false;
	}
	double d = 0;
	return Double.TryParse(val, System.Globalization.NumberStyles.AllowThousands | System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out d);
}

public bool IsNumeric(string val, ref double d)
{
	if (val == null)
	{
		return false;
	}
	return Double.TryParse(val, System.Globalization.NumberStyles.AllowThousands | System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out d);
}

public bool ValToBool(string val)
{
	if (val != null)
	{
		if (string.Compare(val, bool.TrueString, StringComparison.OrdinalIgnoreCase) == 0)
		{
			return true;
		}
		if (string.Compare(val, bool.FalseString, StringComparison.OrdinalIgnoreCase) == 0)
		{
			return false;
		}
		val = val.Trim();
		if (string.Compare(val, bool.TrueString, StringComparison.OrdinalIgnoreCase) == 0)
		{
			return true;
		}
		if (string.Compare(val, bool.FalseString, StringComparison.OrdinalIgnoreCase) == 0)
		{
			return false;
		}
		double d = 0;
		if (IsNumeric(val, ref d))
		{
			return (d &gt; 0);
		}
	}
	return false;
}




	</msxsl:script>

</xsl:stylesheet>
