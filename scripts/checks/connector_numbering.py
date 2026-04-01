from .fzp_checkers import FZPChecker
import re

class FZPConnectorNumberingChecker(FZPChecker):
    def check(self):
        pattern = r'(\d+)'
        numberFinder = re.compile(pattern, re.IGNORECASE)

        connectors = self.fzp_doc.xpath("//connector")

        # Check if any connector has an integer name
        gotInt = False
        for connector in connectors:
            try:
                int(connector.get("name"))
                gotInt = True
                break
            except (ValueError, TypeError):
                continue

        if not gotInt:
            return self.get_result()

        # Check if id or name starts from zero
        idZero = False
        for connector in connectors:
            try:
                connector_id = connector.get("id")
                match = numberFinder.search(connector_id)
                if match and match.group(1) == '0':
                    idZero = True
                    break
            except:
                continue

        nameZero = False
        for connector in connectors:
            if connector.get("name") == "0":
                nameZero = True
                break

        # Check for mismatches
        for connector in connectors:
            idInt = 0
            nameInt = 0
            try:
                connector_id = connector.get("id")
                match = numberFinder.search(connector_id)
                if match is None:
                    continue

                idInt = int(match.group(1))
                nameInt = int(connector.get("name"))

            except (ValueError, TypeError):
                continue

            mismatch = False
            if nameZero and idZero:
                mismatch = (idInt != nameInt)
            elif nameZero:
                mismatch = (idInt != nameInt + 1)
            elif idZero:
                mismatch = (idInt + 1 != nameInt)
            else:
                mismatch = (idInt != nameInt)

            if mismatch:
                self.add_warning(f"Connector mismatch: id={connector_id}, name={connector.get('name')}")

        return self.get_result()

    @staticmethod
    def get_name():
        return "connector_numbering"

    @staticmethod
    def get_description():
        return "Check that connectors with integer names are correctly mapped to connector numbers"
