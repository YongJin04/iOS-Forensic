import os
import sqlite3
from artifact_analyzer.call.contacts import Contact
from artifact_analyzer.call.backuphelper import BackupPathHelper

class ContactAnalyzer:
    def __init__(self, backup_path):
        """
        iOS 백업 폴더 경로를 받아 초기화하는 함수
        """
        self.backup_path = backup_path
        self.contacts = []
        self.backup_helper = BackupPathHelper(backup_path)
        
        # 알려진 iOS 백업에서의 주소록 관련 파일 경로
        self.addressbook_paths = [
            "Library/AddressBook/AddressBook.sqlitedb",
            "private/var/mobile/Library/AddressBook/AddressBook.sqlitedb",
            "HomeDomain/Library/AddressBook/AddressBook.sqlitedb",
            "CameraRollDomain/Library/AddressBook/AddressBook.sqlitedb",
            "HomeDomain/Library/AddressBookImages.sqlitedb"
        ]
        
        self.addressbookimages_paths = [
            "Library/AddressBook/AddressBookImages.sqlitedb",
            "private/var/mobile/Library/AddressBook/AddressBookImages.sqlitedb",
            "HomeDomain/Library/AddressBook/AddressBookImages.sqlitedb",
            "HomeDomain/Library/AddressBookImages.sqlitedb"
        ]

    def find_addressbook_db(self):
        """
        백업 폴더에서 AddressBook.sqlitedb 파일 경로 찾기
        """
        # 1. Manifest.db에서 찾기
        for path in self.addressbook_paths:
            file_path = self.backup_helper.get_file_path_from_manifest(path)
            if file_path and os.path.exists(file_path):
                return file_path
        
        # 2. 알려진 도메인과 경로 조합으로 해시값 계산해서 찾기
        domains = ["AppDomain-com.apple.mobilephone", "HomeDomain", "CameraRollDomain"]
        for domain in domains:
            for path in self.addressbook_paths:
                file_path = self.backup_helper.compute_hash_path(domain, path)
                if file_path:
                    return file_path
        
        # 3. 모든 파일 검사 (느리지만 확실한 방법)
        return self.backup_helper.find_sqlite_with_tables(["ABPerson", "ABMultiValue"])

    def find_addressbook_images_db(self):
        """
        백업 폴더에서 AddressBookImages.sqlitedb 파일 경로 찾기
        """
        # 1. Manifest.db에서 찾기
        for path in self.addressbookimages_paths:
            file_path = self.backup_helper.get_file_path_from_manifest(path)
            if file_path and os.path.exists(file_path):
                return file_path
        
        # 2. 알려진 도메인과 경로 조합으로 해시값 계산해서 찾기
        domains = ["AppDomain-com.apple.mobilephone", "HomeDomain", "CameraRollDomain"]
        for domain in domains:
            for path in self.addressbookimages_paths:
                file_path = self.backup_helper.compute_hash_path(domain, path)
                if file_path:
                    return file_path
        
        # 3. 모든 파일 검사 (느리지만 확실한 방법)
        return self.backup_helper.find_sqlite_with_tables(["ABFullSizeImage"])

    def load_contacts(self):
        """
        주소록 데이터베이스에서 연락처 정보 로드
        """
        address_db_path = self.find_addressbook_db()
        if not address_db_path:
            return False, "AddressBook.sqlitedb 파일을 찾을 수 없습니다."

        try:
            conn = sqlite3.connect(address_db_path)
            cursor = conn.cursor()
            
            # 테이블 구조 확인
            cursor.execute("PRAGMA table_info(ABPerson)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 필수 컬럼 목록
            base_columns = ["ROWID", "First", "Last", "Organization", "Note"]
            
            # 선택적 컬럼 목록 (없어도 되는 컬럼들)
            optional_columns = [
                "Kind", "CreationDate", "ModificationDate",
                "ExternalIdentifier", "ExternalModificationTag", "ExternalUUID", 
                "StoreID", "FirstSortSection", "LastSortSection", 
                "FirstSortLanguageIndex", "LastSortLanguageIndex",
                "PersonLink", "IsPreferredName", "guid", "DisplayFlags"
            ]
            
            # 실제 존재하는 컬럼만 선택
            select_columns = ["ROWID"]
            for col in base_columns[1:] + optional_columns:  # ROWID는 이미 추가했으므로 제외
                if col in columns:
                    select_columns.append(col)
                
            # 쿼리 생성
            query = f"SELECT {', '.join(select_columns)} FROM ABPerson"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            self.contacts.clear()
            for row in rows:
                # 기본 필드 (항상 존재한다고 가정)
                rowid = row[0]
                col_index = 1  # ROWID 다음부터 시작
                
                # 기본 필드 값 가져오기
                first_name = row[col_index] if col_index < len(row) and "First" in select_columns else ""
                col_index += 1 if "First" in select_columns else 0
                
                last_name = row[col_index] if col_index < len(row) and "Last" in select_columns else ""
                col_index += 1 if "Last" in select_columns else 0
                
                organization = row[col_index] if col_index < len(row) and "Organization" in select_columns else ""
                col_index += 1 if "Organization" in select_columns else 0
                
                note = row[col_index] if col_index < len(row) and "Note" in select_columns else ""
                col_index += 1 if "Note" in select_columns else 0
                
                # 선택적 필드 값 가져오기
                kind = row[col_index] if col_index < len(row) and "Kind" in select_columns else None
                col_index += 1 if "Kind" in select_columns else 0
                
                creation_date = row[col_index] if col_index < len(row) and "CreationDate" in select_columns else None
                col_index += 1 if "CreationDate" in select_columns else 0
                
                modification_date = row[col_index] if col_index < len(row) and "ModificationDate" in select_columns else None
                col_index += 1 if "ModificationDate" in select_columns else 0
                
                external_identifier = row[col_index] if col_index < len(row) and "ExternalIdentifier" in select_columns else None
                col_index += 1 if "ExternalIdentifier" in select_columns else 0
                
                external_modification_tag = row[col_index] if col_index < len(row) and "ExternalModificationTag" in select_columns else None
                col_index += 1 if "ExternalModificationTag" in select_columns else 0
                
                external_uuid = row[col_index] if col_index < len(row) and "ExternalUUID" in select_columns else None
                col_index += 1 if "ExternalUUID" in select_columns else 0
                
                store_id = row[col_index] if col_index < len(row) and "StoreID" in select_columns else None
                col_index += 1 if "StoreID" in select_columns else 0
                
                first_sort_section = row[col_index] if col_index < len(row) and "FirstSortSection" in select_columns else None
                col_index += 1 if "FirstSortSection" in select_columns else 0
                
                last_sort_section = row[col_index] if col_index < len(row) and "LastSortSection" in select_columns else None
                col_index += 1 if "LastSortSection" in select_columns else 0
                
                first_sort_language_index = row[col_index] if col_index < len(row) and "FirstSortLanguageIndex" in select_columns else None
                col_index += 1 if "FirstSortLanguageIndex" in select_columns else 0
                
                last_sort_language_index = row[col_index] if col_index < len(row) and "LastSortLanguageIndex" in select_columns else None
                col_index += 1 if "LastSortLanguageIndex" in select_columns else 0
                
                person_link = row[col_index] if col_index < len(row) and "PersonLink" in select_columns else None
                col_index += 1 if "PersonLink" in select_columns else 0
                
                is_preferred_name = row[col_index] if col_index < len(row) and "IsPreferredName" in select_columns else None
                col_index += 1 if "IsPreferredName" in select_columns else 0
                
                guid = row[col_index] if col_index < len(row) and "guid" in select_columns else None
                col_index += 1 if "guid" in select_columns else 0
                
                display_flags = row[col_index] if col_index < len(row) and "DisplayFlags" in select_columns else None
                
                # Contact 객체 생성
                c = Contact(
                    rowid=rowid,
                    first_name=first_name or "",
                    last_name=last_name or "",
                    organization=organization or "",
                    note=note or "",
                    kind=kind,
                    creation_date=creation_date,
                    modification_date=modification_date,
                    external_identifier=external_identifier,
                    external_modification_tag=external_modification_tag,
                    external_uuid=external_uuid,
                    store_id=store_id,
                    first_sort_section=first_sort_section,
                    last_sort_section=last_sort_section,
                    first_sort_language_index=first_sort_language_index,
                    last_sort_language_index=last_sort_language_index,
                    person_link=person_link,
                    is_preferred_name=is_preferred_name,
                    guid=guid,
                    display_flags=display_flags
                )
                self.contacts.append(c)
            
            # ABMultiValue 테이블에서 추가 정보(전화번호, 이메일 등) 가져오기
            cursor.execute("""
                SELECT
                    ABMultiValue.record_id,
                    ABMultiValue.value,
                    ABMultiValueLabel.value
                FROM ABMultiValue
                LEFT JOIN ABMultiValueLabel
                ON ABMultiValue.label = ABMultiValueLabel.ROWID
            """)
            rows = cursor.fetchall()
            
            for rec_id, value, label_value in rows:
                for contact in self.contacts:
                    if contact.rowid == rec_id:
                        contact.add_value(label_value, value)
                        break
            
            conn.close()
            
            # 이미지 로드
            self.load_contact_images()
            
            return True, f"연락처 정보 로드 완료 (총 {len(self.contacts)}개)"
            
        except Exception as e:
            return False, f"연락처 정보 로드 실패: {str(e)}"

    def load_contact_images(self):
        """
        AddressBookImages.sqlitedb 파일에서 연락처 이미지 로드
        """
        images_db_path = self.find_addressbook_images_db()
        if not images_db_path:
            return
        
        try:
            conn = sqlite3.connect(images_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT record_id, data FROM ABFullSizeImage")
            image_rows = cursor.fetchall()
            conn.close()
            
            for record_id, image_data in image_rows:
                for contact in self.contacts:
                    if contact.rowid == record_id:
                        contact.image = image_data
                        break
                        
        except Exception as e:
            print(f"이미지 로드 실패: {str(e)}")  # 오류 발생 시 로그 기록

    def get_contacts(self):
        """
        로드된 연락처 목록 반환
        """
        return self.contacts

    def search_contacts(self, query):
        """
        검색어에 따라 연락처 필터링
        """
        if not query:
            return self.contacts
            
        query = query.lower()
        filtered_contacts = []
        
        for contact in self.contacts:
            full_name = f"{contact.last_name} {contact.first_name}".strip().lower()
            phone = contact.get_phone_number().lower()
            org = contact.organization.lower()
            
            if (query in full_name or query in phone or query in org):
                filtered_contacts.append(contact)
                
        return filtered_contacts