class Contact:
    def __init__(self, rowid, first_name, last_name, organization, note,
                 kind=None, creation_date=None, modification_date=None,
                 external_identifier=None, external_modification_tag=None,
                 external_uuid=None, store_id=None, first_sort_section=None,
                 last_sort_section=None, first_sort_language_index=None,
                 last_sort_language_index=None, person_link=None, is_preferred_name=None,
                 guid=None, display_flags=None):
        """
        연락처 한 건의 정보를 저장하는 클래스.
        기본 정보(이름, 소속, 메모 등)와 추가 정보들을 저장하며,
        라벨별 추가 정보(전화번호, 이메일 등)는 values_by_label 딕셔너리에 저장.
        """
        self.rowid = rowid
        self.first_name = first_name
        self.last_name = last_name
        self.organization = organization
        self.note = note
        self.kind = kind
        self.creation_date = creation_date
        self.modification_date = modification_date
        self.external_identifier = external_identifier
        self.external_modification_tag = external_modification_tag
        self.external_uuid = external_uuid
        self.store_id = store_id
        self.first_sort_section = first_sort_section
        self.last_sort_section = last_sort_section
        self.first_sort_language_index = first_sort_language_index
        self.last_sort_language_index = last_sort_language_index
        self.person_link = person_link
        self.is_preferred_name = is_preferred_name
        self.guid = guid
        self.display_flags = display_flags
        
        # 라벨별 값 저장용: 예) { 'phone': ['01012345678', '01099998888'], 'email': [...] }
        self.values_by_label = {}
        
        self.image = None  # 연락처 이미지 데이터

    def add_value(self, label_name, value):
        """
        ABMultiValueLabel에서 가져온 라벨과 값(value)을 저장.
        라벨이 None인 경우 빈 문자열로 처리.
        """
        if label_name is None:
            label_name = ""
        if label_name not in self.values_by_label:
            self.values_by_label[label_name] = []
        self.values_by_label[label_name].append(value)

    def get_phone_number(self):
        """
        저장된 전화번호들을 포맷팅하여 반환.
        전화번호 라벨이 없는 경우도 포함.
        여러 전화번호가 있을 경우 콤마로 구분된 문자열로 반환.
        """
        # 전화번호로 사용될 라벨 후보 (빈 문자열도 포함)
        phone_labels = {
            "_$!<Mobile>!$_", "_$!<Home>!$_", "_$!<Work>!$_",
            "_$!<Main>!$_", "iPhone", "home", "work", "mobile", ""
        }
        
        all_numbers = []
        for label_name, val_list in self.values_by_label.items():
            if label_name in phone_labels:
                for num in val_list:
                    from artifact_analyzer.call.utils import format_phone_number 
                    formatted_num = format_phone_number(num)
                    all_numbers.append(formatted_num)
        return ", ".join(all_numbers) if all_numbers else ""

    def get_emails(self):
        """
        저장된 이메일 주소들을 반환.
        여러 이메일이 있을 경우 콤마로 구분된 문자열로 반환.
        """
        email_labels = {
            "_$!<Home>!$_", "_$!<Work>!$_", "home", "work", "email", ""
        }
        
        all_emails = []
        for label_name, val_list in self.values_by_label.items():
            if label_name in email_labels:
                for email in val_list:
                    all_emails.append(email)
        return ", ".join(all_emails) if all_emails else ""

    def get_formatted_details(self):
        """
        연락처의 상세 정보를 HTML 형식으로 반환.
        """
        from artifact_analyzer.call.utils import format_mac_time
        creation_str = format_mac_time(self.creation_date) if self.creation_date else "N/A"
        modification_str = format_mac_time(self.modification_date) if self.modification_date else "N/A"
        full_name = f"{self.last_name} {self.first_name}".strip()
        
        return (
            f"<b>이름:</b> {full_name}<br>"
            f"<b>소속:</b> {self.organization}<br>"
            f"<b>전화번호:</b> {self.get_phone_number()}<br>"
            f"<b>이메일:</b> {self.get_emails()}<br>"
            f"<b>메모:</b> {self.note}<br><br>"
            f"<b>생성일:</b> {creation_str} (Mac absolute time : {self.creation_date})<br>"
            f"<b>수정일:</b> {modification_str} (Mac absolute time : {self.modification_date})<br>"
            f"<b>GUID:</b> {self.guid}<br>"
        )