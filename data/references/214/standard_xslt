<?xml version="1.0" encoding="UTF-16"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:var="http://schemas.microsoft.com/BizTalk/2003/var" exclude-result-prefixes="msxsl var s0 userCSharp" version="1.0" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI214/v1.0" xmlns:s0="http://Echo.BSSR.Internal.Canonical.Status/v1.0" xmlns:userCSharp="http://schemas.microsoft.com/BizTalk/2003/userCSharp">
	<xsl:output omit-xml-declaration="yes" method="xml" version="1.0" />
	<xsl:template match="/">
		<xsl:apply-templates select="/s0:Status" />
	</xsl:template>
	<xsl:template match="/s0:Status">

		<ns0:X12_00401_214>
			<ST>
				<ST01>214</ST01>
				<ST02>1234</ST02>
			</ST>
			<xsl:for-each select="StatusList">
				<xsl:for-each select="ShipmentStatus">
					<xsl:for-each select="ReferenceData">
						<ns0:B10>
							<xsl:if test="LoadId/text() != ''">
								<B1001>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="LoadId/text()" />
										<xsl:with-param name="maxLength" select="30" />
									</xsl:call-template>
								</B1001>
							</xsl:if>
							<xsl:if test="Bol/text()  != ''">
								<B1002>
									<xsl:call-template name="CleanAlphaField" >
										<xsl:with-param name="inputText" select="Bol/text()" />
										<xsl:with-param name="maxLength" select="30" />
									</xsl:call-template>
								</B1002>
							</xsl:if>
							<B1003><xsl:choose><xsl:when test="../../eNum/text() = '191806'">ECHS</xsl:when><xsl:otherwise><xsl:value-of select="../../ReferenceData/Scac"/></xsl:otherwise></xsl:choose></B1003>
						</ns0:B10>
					</xsl:for-each>
				</xsl:for-each>
			</xsl:for-each>

			<xsl:for-each select="StatusList">
				<xsl:for-each select="ShipmentStatus">
					<xsl:for-each select="BusinessReferences">
						<xsl:for-each select="BusinessReference">
							<xsl:if test="(@referenceId != '') and (@referenceType  != '')">
								<ns0:L11>
									<xsl:if test="@referenceId != ''">
										<L1101>
											<xsl:call-template name="CleanAlphaField" >
												<xsl:with-param name="inputText" select="@referenceId" />
												<xsl:with-param name="maxLength" select="30" />
											</xsl:call-template>
										</L1101>
									</xsl:if>
									<xsl:choose>
										<xsl:when test="@referenceType = 'ZC' and @referenceDescription = 'Carrier Name'">
											<L1102>ZC</L1102>
										</xsl:when>
										<xsl:otherwise>
											<xsl:if test="@referenceType != ''">
												<L1102>
													<xsl:call-template name="CleanAlphaField" >
														<xsl:with-param name="inputText" select="@referenceType" />
														<xsl:with-param name="maxLength" select="3" />
													</xsl:call-template>
												</L1102>
											</xsl:if>
										</xsl:otherwise>
									</xsl:choose>
									<xsl:if test="@referenceType = 'ZC' and @referenceDescription = 'Carrier Name'">
										<L1103>ZC</L1103>
									</xsl:if>
								</ns0:L11>
							</xsl:if>
						</xsl:for-each>
					</xsl:for-each>
				</xsl:for-each>
			</xsl:for-each>

			<xsl:for-each select="StatusList">
				<xsl:for-each select="ShipmentStatus">
					<xsl:for-each select="Statuses">
						<xsl:for-each select="Status/Details/Detail[@stopType='Pick']">
							<xsl:if test="position()=1">
								<xsl:for-each select="Addresses">
									<xsl:for-each select="Address">
										<!--first one-->
										<ns0:N1Loop1>
											<ns0:N1>
												<xsl:if test="../../@stopType">
													<N101>
														<xsl:call-template name="StopTypeMapValue">
															<xsl:with-param name="ValueToConvert" select="../../@stopType" />
														</xsl:call-template>
													</N101>
												</xsl:if>
												<xsl:if test="@name != ''">
													
														<N102>
															<xsl:call-template name="CleanAlphaField" >
																<xsl:with-param name="inputText" select="@name" />
																<xsl:with-param name="maxLength" select="30" />
															</xsl:call-template>
														</N102>


												</xsl:if>
												<xsl:choose>
													<xsl:when test="@locationIdentifierCode!=''">
														<N103>
															<xsl:choose>
																<xsl:when test="@locationIdentifier !=''">
																	<xsl:value-of select="@locationIdentifier"/>
																</xsl:when>
																<xsl:otherwise>93</xsl:otherwise>
															</xsl:choose>
														</N103>
														<xsl:if test="@locationIdentifier !=''">
															<N104>
																<xsl:value-of select="Addresses/Address/@locationIdentifier"/>
															</N104>
														</xsl:if>
													</xsl:when>
													<xsl:when test="//BusinessReferences/BusinessReference[@referenceType = 'SF' and @referenceDescription='EDIQualifier'] and ../../@stopType = 'Pick'">
														<N103>
															<xsl:choose>
																<xsl:when test="@locationIdentifier !=''">
																	<xsl:value-of select="@locationIdentifier"/>
																</xsl:when>
																<xsl:otherwise>93</xsl:otherwise>
															</xsl:choose>
														</N103>
														<N104>
															<xsl:value-of select="//BusinessReferences/BusinessReference[@referenceType ='SF']/@referenceId"/>
														</N104>
													</xsl:when>
												</xsl:choose>
											</ns0:N1>
											<xsl:if test="@address1 != '' or @address2 != ''">
												<ns0:N3>
													<xsl:if test="@address1 != ''">
														<N301>
															<xsl:call-template name="CleanAlphaField" >
																<xsl:with-param name="inputText" select="@address1" />
																<xsl:with-param name="maxLength" select="30" />
															</xsl:call-template>
														</N301>
													</xsl:if>
													<xsl:if test="@address2 != ''">
														<N302>
															<xsl:call-template name="CleanAlphaField" >
																<xsl:with-param name="inputText" select="@address2" />
																<xsl:with-param name="maxLength" select="30" />
															</xsl:call-template>
														</N302>
													</xsl:if>
												</ns0:N3>
											</xsl:if>
											<ns0:N4>
												<xsl:if test="@city != ''">
													<N401>
														<xsl:call-template name="CleanAlphaField" >
															<xsl:with-param name="inputText" select="@city" />
															<xsl:with-param name="maxLength" select="30" />
														</xsl:call-template>
													</N401>
												</xsl:if>
												<xsl:if test="@stateProvince != ''">
													<N402>
														<xsl:value-of select="@stateProvince" />
													</N402>
												</xsl:if>
												<xsl:if test="@postalCode != ''">
													<N403>
														<xsl:value-of select="@postalCode" />
													</N403>
												</xsl:if>
												<xsl:if test="@country != ''">
													<N404>
														<xsl:value-of select="@country" />
													</N404>
												</xsl:if>
											</ns0:N4>
										</ns0:N1Loop1>
									</xsl:for-each>
								</xsl:for-each>
							</xsl:if>
						</xsl:for-each>
					</xsl:for-each>
				</xsl:for-each>
			</xsl:for-each>
			<xsl:for-each select="StatusList">
				<xsl:for-each select="ShipmentStatus">
					<xsl:for-each select="Statuses">
						<xsl:for-each select="Status/Details/Detail[@stopType='Drop']">
							<xsl:if test="position()=last()">
								<xsl:for-each select="Addresses">
									<xsl:for-each select="Address">
										<!--first one-->
										<ns0:N1Loop1>
											<ns0:N1>
												<xsl:if test="../../@stopType">
													<N101>
														<xsl:call-template name="StopTypeMapValue">
															<xsl:with-param name="ValueToConvert" select="../../@stopType" />
														</xsl:call-template>
													</N101>
												</xsl:if>
												<xsl:if test="@name != ''">
													
														<N102>
															<xsl:call-template name="CleanAlphaField" >
																<xsl:with-param name="inputText" select="@name" />
																<xsl:with-param name="maxLength" select="30" />
															</xsl:call-template>
														</N102>


												</xsl:if>
												<xsl:choose>
													<xsl:when test="Addresses/Address/@locationIdentifierCode!=''">
														<N103>
															<xsl:choose>
																<xsl:when test="@locationIdentifier !=''">
																	<xsl:value-of select="@locationIdentifier"/>
																</xsl:when>
																<xsl:otherwise>93</xsl:otherwise>
															</xsl:choose>
														</N103>
														<N104>
															<xsl:value-of select="Addresses/Address/@locationIdentifier"/>
														</N104>
													</xsl:when>
													<xsl:when test="//BusinessReferences/BusinessReference[@referenceType = 'ST' and @referenceDescription='EDIQualifier'] and ../../@stopType = 'Drop'">
														<N103>
															<xsl:choose>
																<xsl:when test="@locationIdentifier !=''">
																	<xsl:value-of select="@locationIdentifier"/>
																</xsl:when>
																<xsl:otherwise>93</xsl:otherwise>
															</xsl:choose>
														</N103>
														<N104>
															<xsl:value-of select="//BusinessReferences/BusinessReference[@referenceType = 'ST']/@referenceId"/>
														</N104>
													</xsl:when>
												</xsl:choose>
											</ns0:N1>
											<xsl:if test="@address1 != '' or @address2 != ''">
												<ns0:N3>
													<xsl:if test="@address1 != ''">
														<N301>
															<xsl:call-template name="CleanAlphaField" >
																<xsl:with-param name="inputText" select="@address1" />
																<xsl:with-param name="maxLength" select="30" />
															</xsl:call-template>
														</N301>
													</xsl:if>
													<xsl:if test="@address2 != ''">
														<N302>
															<xsl:call-template name="CleanAlphaField" >
																<xsl:with-param name="inputText" select="@address2" />
																<xsl:with-param name="maxLength" select="30" />
															</xsl:call-template>
														</N302>
													</xsl:if>
												</ns0:N3>
											</xsl:if>
											<ns0:N4>
												<xsl:if test="@city != ''">
													<N401>
														<xsl:call-template name="CleanAlphaField" >
															<xsl:with-param name="inputText" select="@city" />
															<xsl:with-param name="maxLength" select="30" />
														</xsl:call-template>
													</N401>
												</xsl:if>
												<xsl:if test="@stateProvince != ''">
													<N402>
														<xsl:value-of select="@stateProvince" />
													</N402>
												</xsl:if>
												<xsl:if test="@postalCode != ''">
													<N403>
														<xsl:value-of select="@postalCode" />
													</N403>
												</xsl:if>
												<xsl:if test="@country != ''">
													<N404>
														<xsl:value-of select="@country" />
													</N404>
												</xsl:if>
											</ns0:N4>
										</ns0:N1Loop1>
									</xsl:for-each>
								</xsl:for-each>
							</xsl:if>
						</xsl:for-each>
					</xsl:for-each>
				</xsl:for-each>
			</xsl:for-each>


			<xsl:for-each select="StatusList">
				<xsl:for-each select="ShipmentStatus">
					<xsl:for-each select="Statuses">
						<xsl:for-each select="Status[Details/Detail/@statusCode !='']">

							<ns0:LXLoop1>
								<ns0:LX>
									<xsl:if test="@assignedNumber != ''">
										<LX01>
											<xsl:value-of select="@assignedNumber" />
										</LX01>
									</xsl:if>
								</ns0:LX>
								<xsl:for-each select="Details/Detail">
									<ns0:AT7Loop1>
										<ns0:AT7>
											<xsl:if test="(@statusCode != 'AA' and @statusCode != 'AB')">
												<xsl:if test="@statusCode !=''">
													<AT701>
														<xsl:value-of select="@statusCode" />
													</AT701>
													<AT702>NS</AT702>
												</xsl:if>
												<xsl:if test="(@statusCode = 'AA' or @statusCode = 'AB')">
													<AT703>
														<xsl:value-of select="@statusCode" />
													</AT703>
													<AT704>NA</AT704>
												</xsl:if>
											</xsl:if>
											<xsl:if test="@statusdatetime != ''">
												<AT705>
													<xsl:value-of select="concat(substring(@statusdatetime, 1, 4), substring(@statusdatetime, 6, 2), substring(@statusdatetime, 9, 2))" />
												</AT705>
											</xsl:if>
											<xsl:if test="@statusdatetime != ''">
												<AT706>
													<xsl:value-of select="concat(substring(@statusdatetime, 12, 2), substring(@statusdatetime, 15, 2))" />
												</AT706>
											</xsl:if>
											<AT707>
												<xsl:choose>
													<xsl:when test="@statusCode = 'AA'">
														<xsl:value-of select="@statusTimeZone"/>
													</xsl:when>
													<xsl:otherwise>LT</xsl:otherwise>
												</xsl:choose>
											</AT707>
										</ns0:AT7>
										<xsl:if test="(EquipmentLocation/@cityName != '') and (EquipmentLocation/@stateOrProvince != '') ">
											<ns0:MS1>
												<xsl:if test="EquipmentLocation/@cityName != ''">
													<MS101>
														<xsl:call-template name="CleanAlphaField" >
															<xsl:with-param name="inputText" select="EquipmentLocation/@cityName" />
															<xsl:with-param name="maxLength" select="30" />
														</xsl:call-template>
													</MS101>
												</xsl:if>
												<xsl:if test="EquipmentLocation/@stateOrProvince != ''">
													<MS102>
														<xsl:value-of select="EquipmentLocation/@stateOrProvince" />
													</MS102>
												</xsl:if>
											</ns0:MS1>
										</xsl:if>
										<ns0:MS2>
											<MS201>ECHS</MS201>
											<xsl:choose>
												<xsl:when test="EquipmentLocation/@equipmentNumber != '' and EquipmentLocation/@equipmentDescriptionCode !=''">
													<MS202>
														<xsl:call-template name="CleanAlphaField" >
															<xsl:with-param name="inputText" select="EquipmentLocation/@equipmentNumber" />
															<xsl:with-param name="maxLength" select="10" />
														</xsl:call-template>
													</MS202>
												</xsl:when>
												<xsl:otherwise>
													<MS202>UNKNOWN</MS202>
												</xsl:otherwise>
											</xsl:choose>
											<MS203>TL</MS203>
										</ns0:MS2>
									</ns0:AT7Loop1>
								</xsl:for-each>
								<xsl:for-each select="../../ReferenceData">
									<xsl:if test="(StopSequenceNumber/text()  != '') and (StopSequenceNumber/text()  != 0)">
										<ns0:L11_3>
											<L1101>
												<xsl:call-template name="CleanAlphaField" >
													<xsl:with-param name="inputText" select="StopSequenceNumber/text()" />
													<xsl:with-param name="maxLength" select="30" />
												</xsl:call-template>
											</L1101>
											<L1102>QN</L1102>
										</ns0:L11_3>
									</xsl:if>
								</xsl:for-each>

								<xsl:for-each select="../../Remarks">
									<xsl:for-each select="Remark">
										<xsl:if test="(@remarkMessage2 != '') and (@remarkMessage1=//Details/Detail/@statusCode)">
											<ns0:K1_2>
												<K101>
													<xsl:call-template name="CleanAlphaField" >
														<xsl:with-param name="inputText" select="@remarkMessage2" />
														<xsl:with-param name="maxLength" select="30" />
													</xsl:call-template>
												</K101>
												<K102>Notes</K102>
											</ns0:K1_2>
										</xsl:if>
									</xsl:for-each>
								</xsl:for-each>

								<xsl:for-each select="../../ShipmentTotals">
									<xsl:if test="TotalWeight != '' and  TotalWeight> 0 ">
										<ns0:AT8>
											<AT801>B</AT801>
											<AT802>L</AT802>
											<AT803>
												<xsl:value-of select="format-number(TotalWeight/text(), '0.##')" />
											</AT803>
											<xsl:if test="TotalHandlingQty > 0">
												<AT804>
													<xsl:value-of select="TotalHandlingQty/text()" />
												</AT804>
											</xsl:if>
										</ns0:AT8>
									</xsl:if>
								</xsl:for-each>
							</ns0:LXLoop1>
						</xsl:for-each>
					</xsl:for-each>
				</xsl:for-each>
			</xsl:for-each>
			<SE>
				<SE01>214</SE01>
				<SE02>1234</SE02>
			</SE>
		</ns0:X12_00401_214>
	</xsl:template>

	<!--Custom Templates-->
	<!--Value mapping template-->
	<xsl:template name="StopTypeMapValue">
		<xsl:param name="ValueToConvert" select="0" />
		<xsl:variable name="StopTypeMap" >
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
			<xsl:value-of select="$pNode" />
		</xsl:if>
		<xsl:if test="not($pNode)">
			<xsl:value-of select="$pDefaultValue"/>
		</xsl:if>
	</xsl:template>
	<!--Set default if empty template end-->

	<!-- CleanAlphaField start  -->
	<xsl:template name="CleanAlphaField">
		<xsl:param name="inputText" />
		<xsl:param name="maxLength" />
		<xsl:variable name="singleQuote" select='"&apos;"' />
		<xsl:variable name="doubleQuote" select="'&quot;'" />
		<xsl:variable name="vAllowedSymbolsPart1" select="'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890 !@$%()+-_,.;=[]{}\?/#'"/>
		<xsl:variable name="vAllowedSymbols" select="concat($vAllowedSymbolsPart1, $singleQuote, $doubleQuote)"/>
		<xsl:variable name="vCleanedText" select="translate($inputText,translate($inputText, $vAllowedSymbols, ''),'')"/>
		<xsl:value-of select="substring(normalize-space($vCleanedText), 1, $maxLength)"/>
	</xsl:template>
	<!-- Clean AlphaField end -->
	
</xsl:stylesheet>