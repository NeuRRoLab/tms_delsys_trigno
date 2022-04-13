"""
This class creates an instance of the Trigno base. Put in your key and license here
"""
import clr
clr.AddReference("resources/DelsysAPI")
clr.AddReference("System.Collections")


from Aero import AeroPy

key = "***REMOVED***"
license = "<License>\n  <Id>17cbdad2-eee4-4102-9f94-8d28bc800bb7</Id>\n  <Type>Standard</Type>\n  <Quantity>10</Quantity>\n  <LicenseAttributes>\n    <Attribute name=\"Software\">VS2012</Attribute>\n  </LicenseAttributes>\n  <ProductFeatures>\n    <Feature name=\"Sales\">True</Feature>\n    <Feature name=\"Billing\">False</Feature>\n  </ProductFeatures>\n  <Customer>\n    <Name>Chandramouli Krishnan</Name>\n    <Email>moulli@med.umich.edu</Email>\n  </Customer>\n  <Expiration>Tue, 13 Apr 2032 04:00:00 GMT</Expiration>\n  <Signature>***REMOVED***</Signature>\n</License>"
# license = "<License>\r\n  <Id>9806a806-a0a1-4351-9cc1-86f45c288fed</Id>\r\n  <Type>Standard</Type>\r\n  <Quantity>10</Quantity>\r\n  <LicenseAttributes>\r\n    <Attribute name=\"Software\">VS2012</Attribute>\r\n  </LicenseAttributes>\r\n  <ProductFeatures>\r\n    <Feature name='Sales'>True</Feature>\r\n    <Feature name='Billing'>False</Feature>\r\n  </ProductFeatures>\r\n  <Customer>\r\n    <Name>Luis Cubillos</Name>\r\n    <Email>lhcubill@umich.edu</Email>\r\n  </Customer>\r\n  <Expiration>Wed, 01 Jan 2031 05:00:00 GMT</Expiration>\r\n  <Signature>MEUCIQDaULT2mNHWtHCQwohQSBwumS2fpjHLn5DkiRfQEIvyWgIgYKFjth1NLMBNEMiTK2QbcB6iXPeETKKCtujRtJIrFmg=</Signature>\r\n</License>"
class TrignoBase():
    def __init__(self):
        self.BaseInstance = AeroPy()