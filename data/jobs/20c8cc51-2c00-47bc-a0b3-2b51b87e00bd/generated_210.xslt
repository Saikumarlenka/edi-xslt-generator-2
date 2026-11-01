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
				<!-- B301 is crossed out in matrix; commented out in XSLT
				<xsl:if xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp" test="Header/BeginningSegmentForCarriersInvoice/@ShipmentQualifier != '' ">      
					<B301><xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@ShipmentQualifier"/></B301>
				</xsl:if>
        -->
				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@InvoiceNumber != ''">
					<B302>
						<xsl:call-template name="CleanAlphaField">
							<xsl:with-param name="inputText" select="Header/BeginningSegmentForCarriersInvoice/@InvoiceNumber"/>
							<xsl:with-param name="maxLength" select="22"/>
						</xsl:call-template>
					</B302>
				</xsl:if>
				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@ShipmentIdentificationNumber != ''">
					<B303>
						<xsl:call-template name="CleanAlphaField">
							<xsl:with-param name="inputText" select="Header/BeginningSegmentForCarriersInvoice/@ShipmentIdentificationNumber"/>
							<xsl:with-param name="maxLength" select="30"/>
						</xsl:call-template>
					</B303>
				</xsl:if>
				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@ShipmentMethodOfPayment != '' ">
					<B304>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@ShipmentMethodOfPayment"/>
					</B304>
				</xsl:if>
				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@WeightUnitCode != '' ">
					<B305>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@WeightUnitCode"/>
					</B305>
				</xsl:if>
				<xsl:variable name="InvoiceDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='InvoiceDate']"/>
				<xsl:variable name="DeliveryDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='DeliveryDate']"/>
				<xsl:variable name="BillingDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='BillingDate']"/>
				<xsl:variable name="PickupDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='PickupDate']"/>
				<xsl:if test="$InvoiceDate != '' ">
					<B306>
						<xsl:value-of select="concat(substring($InvoiceDate, 1, 4), substring($InvoiceDate, 6, 2), substring($InvoiceDate, 9, 2))"/>
					</B306>
				</xsl:if>
				<xsl:if test="Header/BeginningSegmentForCarriersInvoice/@NetAmountDue != '' ">
					<B307>
						<xsl:value-of select="translate(Header/BeginningSegmentForCarriersInvoice/@NetAmountDue,'.','')"/>
					</B307>
				</xsl:if>
				<!-- B308 is crossed out in matrix; commented out in XSLT
				<xsl:if xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp" test="Header/BeginningSegmentForCarriersInvoice/@CorrectionIndicator != '' ">
					<B308><xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@CorrectionIndicator"/></B308>
				</xsl:if>
        -->
				<xsl:if test="$DeliveryDate != '' ">
					<B309>
						<xsl:value-of select="concat(substring($DeliveryDate, 1, 4), substring($DeliveryDate, 6, 2), substring($DeliveryDate, 9, 2))"/>
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
				<xsl:if test="$PickupDate != '' ">
					<B312>
						<xsl:value-of select="concat(substring($PickupDate, 1, 4), substring($PickupDate, 6, 2), substring($PickupDate, 9, 2))"/>
					</B312>
				</xsl:if>
				<!-- B313 is crossed out in matrix; commented out in XSLT
				<xsl:if xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp" test="Header/BeginningSegmentForCarriersInvoice/@TariffServiceCode != '' ">
					<B313>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@TariffServiceCode"/>
					</B313>
				</xsl:if>
        -->
				<!-- B314 is crossed out in matrix; commented out in XSLT
				<xsl:if xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp" test="Header/BeginningSegmentForCarriersInvoice/@TransportationTermsCode != '' ">
					<B314>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@TransportationTermsCode"/>
					</B314>
				</xsl:if>
        -->
			</ns0:B3>
			<ns0:C2>
				<C201>R</C201>
				<C202>25</C202>
				<C203>TFP-001</C203>
			</ns0:C2>
			<xsl:if test="Header/Currency/@BillingCurrencyCode != '' ">
				<ns0:C3>
					<C301>
						<xsl:value-of select="Header/Currency/@BillingCurrencyCode"/>
					</C301>
				</ns0:C3>
			</xsl:if>
			<xsl:for-each select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation']">
				<xsl:if test="(@EDICode='BM' or @EDICode='PO') and @ReferenceInformation != '' ">
					<ns0:N9>
						<N901>
							<xsl:value-of select="@EDICode"/>
						</N901>
						<N902>
							<xsl:call-template name="CleanAlphaField">
								<xsl:with-param name="inputText" select="@ReferenceInformation"/>
								<xsl:with-param name="maxLength" select="30"/>
							</xsl:call-template>
						</N902>
					</ns0:N9>
				</xsl:if>
			</xsl:for-each>
			<xsl:variable name="DeliveryDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='DeliveryDate']"/>
			<xsl:variable name="PickupDate" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@*[local-name()='PickupDate']"/>
			<ns0:G62>
				<G6201>10</G6201>
				<G6202>
					<xsl:value-of select="concat(substring($PickupDate, 1, 4), substring($PickupDate, 6, 2), substring($PickupDate, 9, 2))"/>
				</G6202>
			</ns0:G62>
			<ns0:G62>
				<G6201>35</G6201>
				<G6202>
					<xsl:value-of select="concat(substring($DeliveryDate, 1, 4), substring($DeliveryDate, 6, 2), substring($DeliveryDate, 9, 2))"/>
				</G6202>
			</ns0:G62>

			<!-- Segment R3 is not active in matrix; commented out in XSLT
				<ns0:R3 xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp">
				<R301>ECHS</R301>
				<R302>B</R302>
				<R304>M</R304>
				<R306>
					<xsl:value-of select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='BeginningSegmentForCarriersInvoice']/@InvoiceNumber"/>
				</R306>
				<R310>G2</R310>
			</ns0:R3>
        -->

			<!-- Segment K1 is not active in matrix; commented out in XSLT
				<ns0:K1 xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp">
				<xsl:variable name="BMRefInfo" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation'][@EDICode='BM']"/>
				<K101>
					<xsl:choose>
						<xsl:when test="$BMRefInfo &gt; ' ' ">
							<xsl:value-of select="$BMRefInfo"/> 
						</xsl:when>
						<xsl:otherwise>
							<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@ShipmentIdentificationNumber"/>
						</xsl:otherwise> 
					</xsl:choose> 
				</K101>
			</ns0:K1>
        -->

			<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode='BT']">
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
							<xsl:if test="AddressInformation/@AddressInformationLine2 != ''">
								<N302>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine2"/>
										<xsl:with-param name="maxLength" select="55"/>
									</xsl:call-template>
								</N302>
							</xsl:if>
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

			<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode='SH'][1]">
				<ns0:N1Loop1>
					<ns0:N1>
						<N101>SF</N101>
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
							<xsl:if test="AddressInformation/@AddressInformationLine2 != ''">
								<N302>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine2"/>
										<xsl:with-param name="maxLength" select="55"/>
									</xsl:call-template>
								</N302>
							</xsl:if>
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

			<xsl:for-each select="Header/PartyList/Party[Name/@EntityIdentifierCode='CN'][1]">
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
							<xsl:if test="AddressInformation/@AddressInformationLine2 != ''">
								<N302>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="AddressInformation/@AddressInformationLine2"/>
										<xsl:with-param name="maxLength" select="55"/>
									</xsl:call-template>
								</N302>
							</xsl:if>
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
			<xsl:variable name="NumberOfN7" select="count (Header/EquipmentList/Equipment[@EquipmentNumber != ''])"/>
			<xsl:if test="$NumberOfN7 &gt; 0">
				<ns0:N7Loop1>
					<xsl:for-each select="Header/EquipmentList/Equipment">
						<ns0:N7>
							<xsl:if test="@EquipmentNumber != ''">
								<N702>
									<xsl:value-of select="@EquipmentNumber"/>
								</N702>
							</xsl:if>
							<xsl:if test="@EquipmentDescriptionCode != ''">
								<N711>
									<xsl:value-of select="@EquipmentDescriptionCode"/>
								</N711>
							</xsl:if>
							<xsl:if test="@EquipmentDescriptionCode != ''">
								<N715>
									<xsl:value-of select="@EquipmentLength"/>
								</N715>
							</xsl:if>
						</ns0:N7>
					</xsl:for-each>
				</ns0:N7Loop1>
			</xsl:if>
			<!-- Segment S5Loop1 is not active in matrix; commented out in XSLT
				<ns0:S5Loop1 xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp">
				<ns0:S5>
					<S501>
						<xsl:value-of select="position()"/>
					</S501>
					<S502>PU</S502>
					<xsl:if test="../../../Summary/TotalWeightAndCharges/@Weight">
						<S503>
							<xsl:value-of select="../../../Summary/TotalWeightAndCharges/@Weight"/>
						</S503>
						<S504>L</S504>
					</xsl:if>
				</ns0:S5>
				<xsl:for-each select="../../ReferenceList/ReferenceInformation">
					<xsl:if test="(@ReferenceInformationQualifier != '') or (@ReferenceInformation != '') ">
						<ns0:N9_3>
							<xsl:if test="@EDICode != '' ">
								<N901>
									<xsl:value-of select="@EDICode"/>
								</N901>
							</xsl:if>
							<xsl:if test="@ReferenceInformation != '' ">
								<N902>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="@ReferenceInformation"/>
										<xsl:with-param name="maxLength" select="30"/>
									</xsl:call-template>
								</N902>
							</xsl:if>
						</ns0:N9_3>
					</xsl:if>
				</xsl:for-each>
			</ns0:S5Loop1>
        -->

			<xsl:for-each select="Detail/LineItemList/LineItem">
				<ns0:LXLoop1>
					<ns0:LX>
						<LX01>
							<xsl:value-of select="position()"/>
						</LX01>
					</ns0:LX>
					<ns0:L5>
						<L501>
							<xsl:value-of select="position()"/>
						</L501>
						<xsl:if test="DescriptionMarksAndNumbers/@LadingDescription != ''">
							<L502>
								<xsl:call-template name="CleanAlphaField">
									<xsl:with-param name="inputText" select="DescriptionMarksAndNumbers/@LadingDescription"/>
									<xsl:with-param name="maxLength" select="50"/>
								</xsl:call-template>
							</L502>
						</xsl:if>
					</ns0:L5>
					<xsl:if test="RateAndCharges/@SpecialChargeOrAllowanceCode = 'LHS'">
						<ns0:L0>
							<L001>
								<xsl:value-of select="position()"/>
							</L001>
							<xsl:if test="LineItemQuantityAndWeight/@BilledRatedAsQuantity != ''">
								<L002>
									<xsl:value-of select="LineItemQuantityAndWeight/@BilledRatedAsQuantity"/>
								</L002>
							</xsl:if>
							<xsl:if test="LineItemQuantityAndWeight/@BilledRatedAsQualifier != ''">
								<L003>
									<xsl:value-of select="LineItemQuantityAndWeight/@BilledRatedAsQualifier"/>
								</L003>
							</xsl:if>
							<xsl:if test="//Summary/TotalWeightAndCharges/@Weight != ''">
								<L004>
									<xsl:value-of select="//Summary/TotalWeightAndCharges/@Weight"/>
								</L004>
								<L005>L</L005>
							</xsl:if>
							<xsl:if test="//Summary/TotalWeightAndCharges/@LadingQuantity != ''">
								<L008>
									<xsl:value-of select="//Summary/TotalWeightAndCharges/@LadingQuantity"/>
								</L008>
								<L009>PLT</L009>
							</xsl:if>
							<xsl:if test="LineItemQuantityAndWeight/@WeightUnitCode != ''">
								<L011>
									<xsl:value-of select="LineItemQuantityAndWeight/@WeightUnitCode"/>
								</L011>
							</xsl:if>
						</ns0:L0>
					</xsl:if>
					<xsl:if test="RateAndCharges/@FreightRate != '' or RateAndCharges/@Charge != '' or RateAndCharges/@SpecialChargeOrAllowanceCode != ''">
						<ns0:L1>
							<L101>
								<xsl:value-of select="position()"/>
							</L101>
							<xsl:if test="RateAndCharges/@FreightRate != ''">
								<L102>
									<xsl:value-of select="RateAndCharges/@FreightRate"/>
								</L102>
							</xsl:if>
							<xsl:if test="RateAndCharges/@RateValueQualifier != ''">
								<L103>
									<xsl:value-of select="RateAndCharges/@RateValueQualifier"/>
								</L103>
							</xsl:if>
							<xsl:if test="RateAndCharges/@Charge != ''">
								<L104>
									<xsl:value-of select="RateAndCharges/@Charge"/>
								</L104>
							</xsl:if>
							<!-- L107 is crossed out in matrix; commented out in XSLT
				<xsl:if xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp" test="RateAndCharges/@RateCombinationPointCode != ''">
								<L107>
									<xsl:value-of select="RateAndCharges/@RateCombinationPointCode"/>
								</L107>
							</xsl:if>
        -->
							<xsl:choose>
								<xsl:when test="RateAndCharges/@SpecialChargeOrAllowanceCode = '405'">
									<L108>FUE</L108>
								</xsl:when>
								<xsl:otherwise>
									<xsl:if test="RateAndCharges/@SpecialChargeOrAllowanceCode != '' and RateAndCharges/@SpecialChargeOrAllowanceCode != 'LHS'">
										<L108>
											<xsl:value-of select="RateAndCharges/@SpecialChargeOrAllowanceCode"/>
										</L108>
									</xsl:if>
								</xsl:otherwise>
							</xsl:choose>
							<!-- L112 is crossed out in matrix; commented out in XSLT
				<xsl:if xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp" test="RateAndCharges/@SpecialChargeDescription != ''">
								<L112>
									<xsl:call-template name="CleanAlphaField">
										<xsl:with-param name="inputText" select="RateAndCharges/@SpecialChargeDescription"/>
										<xsl:with-param name="maxLength" select="25"/>
									</xsl:call-template>
								</L112>
							</xsl:if>
        -->
						</ns0:L1>
					</xsl:if>
					<xsl:if test="//DescriptionMarksAndNumbers/@CommodityCode2 != ''">
						<!-- Segment L7 is not active in matrix; commented out in XSLT
				<ns0:L7 xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" xmlns:s0="http://Echo.BSSR.Internal.Canonical.InvoiceV2" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp">
							<L701>
								<xsl:value-of select="position()"/>
							</L701>
							<L707>
								<xsl:value-of select="//DescriptionMarksAndNumbers[@CommodityCode2 != '']/@CommodityCode2"/>
							</L707>
						</ns0:L7>
        -->
					</xsl:if>
				</ns0:LXLoop1>
			</xsl:for-each>

			<xsl:for-each select="Summary/TotalWeightAndCharges">
				<ns0:L3>
					<xsl:if test="@Weight">
						<L301>
							<xsl:value-of select="@Weight"/>
						</L301>
					</xsl:if>
					<xsl:if test="@WeightQualifier">
						<L302>G</L302>
					</xsl:if>
					<xsl:variable name="TotalCharges" select="@TotalCharges"/>
					<xsl:variable name="TotalChargesLength" select="string-length(@TotalCharges)"/>
					<xsl:if test="$TotalChargesLength &gt; 2">
						<L305>
							<xsl:value-of select="translate(@TotalCharges,',','')"/>
						</L305>
					</xsl:if>
					<xsl:if test="@LadingQuantity">
						<L311>
							<xsl:value-of select="@LadingQuantity"/>
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

</xsl:stylesheet>
