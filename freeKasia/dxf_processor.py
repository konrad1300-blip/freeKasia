"""
Moduł przetwarzania plików DXF
Ekstrakcja właściwości wektorowych z rysunków DXF
"""

import ezdxf
from ezdxf.math import Vec3
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DXFProcessor:
    """Klasa do przetwarzania plików DXF i ekstrakcji właściwości"""
    
    def __init__(self):
        self.properties = {
            "lengths": [],  # Długości w metrach bieżących
            "areas": [],    # Powierzchnie w metrach kwadratowych
            "quantities": [],  # Ilości elementów
            "times": [],    # Czasy wykonania w godzinach
            "elements": []  # Lista elementów z właściwościami
        }
    
    def process_dxf_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Przetwarza plik DXF i ekstrahuje właściwości
        
        Args:
            file_path: Ścieżka do pliku DXF
            
        Returns:
            Słownik z wyekstrahowanymi właściwościami
        """
        try:
            logger.info(f"Przetwarzanie pliku DXF: {file_path}")
            
            # Wczytanie pliku DXF
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            # Resetowanie właściwości
            self.properties = {
                "lengths": [],
                "areas": [],
                "quantities": [],
                "times": [],
                "elements": []
            }
            
            # Przetwarzanie obiektów w modelspace
            for entity in msp:
                self._process_entity(entity)
            
            # Obliczanie statystyk
            stats = self._calculate_statistics()
            
            logger.info(f"Przetworzono {len(self.properties['elements'])} elementów")
            
            return {
                "file_name": file_path.name,
                "properties": self.properties,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Błąd przetwarzania pliku {file_path}: {str(e)}")
            return {
                "file_name": file_path.name,
                "error": str(e),
                "properties": self.properties,
                "statistics": {}
            }
    
    def _process_entity(self, entity) -> None:
        """Przetwarza pojedynczy obiekt DXF"""
        try:
            entity_type = entity.dxftype()
            
            # Linie - długości
            if entity_type == "LINE":
                length = self._calculate_line_length(entity)
                self.properties["lengths"].append(length)
                self.properties["elements"].append({
                    "type": "LINE",
                    "length": length,
                    "layer": entity.dxf.layer,
                    "start": list(entity.dxf.start),
                    "end": list(entity.dxf.end)
                })
            
            # Polilinie - długości
            elif entity_type in ["LWPOLYLINE", "POLYLINE"]:
                length = self._calculate_polyline_length(entity)
                area = self._calculate_polyline_area(entity)
                self.properties["lengths"].append(length)
                if area > 0:
                    self.properties["areas"].append(area)
                self.properties["elements"].append({
                    "type": entity_type,
                    "length": length,
                    "area": area,
                    "layer": entity.dxf.layer
                })
            
            # Okręgi - obwody i powierzchnie
            elif entity_type == "CIRCLE":
                radius = entity.dxf.radius
                circumference = 2 * 3.14159 * radius
                area = 3.14159 * radius ** 2
                self.properties["lengths"].append(circumference)
                self.properties["areas"].append(area)
                self.properties["elements"].append({
                    "type": "CIRCLE",
                    "radius": radius,
                    "circumference": circumference,
                    "area": area,
                    "layer": entity.dxf.layer
                })
            
            # Łuki - długości
            elif entity_type == "ARC":
                length = self._calculate_arc_length(entity)
                self.properties["lengths"].append(length)
                self.properties["elements"].append({
                    "type": "ARC",
                    "length": length,
                    "layer": entity.dxf.layer
                })
            
            # Elipsy - obwody i powierzchnie
            elif entity_type == "ELLIPSE":
                major_axis = entity.dxf.major_axis
                ratio = entity.dxf.ratio
                # Przybliżony obwód elipsy
                a = major_axis.magnitude
                b = a * ratio
                circumference = 3.14159 * (3*(a+b) - ((3*a+b)*(a+3*b))**0.5)
                area = 3.14159 * a * b
                self.properties["lengths"].append(circumference)
                self.properties["areas"].append(area)
                self.properties["elements"].append({
                    "type": "ELLIPSE",
                    "circumference": circumference,
                    "area": area,
                    "layer": entity.dxf.layer
                })
            
            # Spline - długości przybliżone
            elif entity_type == "SPLINE":
                length = self._calculate_spline_length(entity)
                self.properties["lengths"].append(length)
                self.properties["elements"].append({
                    "type": "SPLINE",
                    "length": length,
                    "layer": entity.dxf.layer
                })
            
            # Bloki - ilości
            elif entity_type == "INSERT":
                self.properties["quantities"].append(1)
                self.properties["elements"].append({
                    "type": "BLOCK",
                    "name": entity.dxf.name,
                    "layer": entity.dxf.layer,
                    "insertion_point": list(entity.dxf.insert)
                })
            
            # Tekst - ilości
            elif entity_type in ["TEXT", "MTEXT"]:
                self.properties["quantities"].append(1)
                self.properties["elements"].append({
                    "type": entity_type,
                    "layer": entity.dxf.layer
                })
            
            # Wymiary - ilości
            elif entity_type == "DIMENSION":
                self.properties["quantities"].append(1)
                self.properties["elements"].append({
                    "type": "DIMENSION",
                    "layer": entity.dxf.layer
                })
                
        except Exception as e:
            logger.warning(f"Błąd przetwarzania obiektu {entity.dxftype()}: {str(e)}")
    
    def _calculate_line_length(self, line) -> float:
        """Oblicza długość linii"""
        start = Vec3(line.dxf.start)
        end = Vec3(line.dxf.end)
        return (end - start).magnitude
    
    def _calculate_polyline_length(self, polyline) -> float:
        """Oblicza długość polilinii"""
        try:
            if polyline.dxftype() == "LWPOLYLINE":
                points = list(polyline.get_points(format="xy"))
            else:
                points = [vertex.dxf.location for vertex in polyline.vertices]
            
            length = 0.0
            for i in range(len(points) - 1):
                p1 = Vec3(points[i])
                p2 = Vec3(points[i + 1])
                length += (p2 - p1).magnitude
            
            # Jeśli polilinia jest zamknięta, dodaj ostatni odcinek
            if polyline.closed:
                p1 = Vec3(points[-1])
                p2 = Vec3(points[0])
                length += (p2 - p1).magnitude
            
            return length
        except:
            return 0.0
    
    def _calculate_polyline_area(self, polyline) -> float:
        """Oblicza powierzchnię polilinii (jeśli zamknięta)"""
        try:
            if not polyline.closed:
                return 0.0
            
            if polyline.dxftype() == "LWPOLYLINE":
                points = list(polyline.get_points(format="xy"))
            else:
                points = [vertex.dxf.location for vertex in polyline.vertices]
            
            # Wzór Shoelace do obliczania powierzchni
            n = len(points)
            area = 0.0
            for i in range(n):
                j = (i + 1) % n
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
            
            return abs(area) / 2.0
        except:
            return 0.0
    
    def _calculate_arc_length(self, arc) -> float:
        """Oblicza długość łuku"""
        try:
            radius = arc.dxf.radius
            start_angle = arc.dxf.start_angle
            end_angle = arc.dxf.end_angle
            
            # Obliczanie kąta w radianach
            if end_angle < start_angle:
                angle = (360 - start_angle + end_angle) * 3.14159 / 180
            else:
                angle = (end_angle - start_angle) * 3.14159 / 180
            
            return radius * angle
        except:
            return 0.0
    
    def _calculate_spline_length(self, spline) -> float:
        """Oblicza przybliżoną długość spline'a"""
        try:
            # Przybliżenie przez sumowanie odcinków między punktami kontrolnymi
            points = spline.control_points
            length = 0.0
            for i in range(len(points) - 1):
                p1 = Vec3(points[i])
                p2 = Vec3(points[i + 1])
                length += (p2 - p1).magnitude
            return length
        except:
            return 0.0
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """Oblicza statystyki z przetworzonych danych"""
        stats = {
            "total_elements": len(self.properties["elements"]),
            "total_length": sum(self.properties["lengths"]),
            "total_area": sum(self.properties["areas"]),
            "total_quantity": len(self.properties["quantities"]),
            "length_count": len(self.properties["lengths"]),
            "area_count": len(self.properties["areas"]),
            "quantity_count": len(self.properties["quantities"])
        }
        
        # Szacowanie czasów wykonania (przykładowe współczynniki)
        # Można dostosować na podstawie rzeczywistych danych
        estimated_time = (stats["total_length"] * 0.1 + 
                         stats["total_area"] * 0.5 + 
                         stats["total_quantity"] * 0.2)
        stats["estimated_time_hours"] = round(estimated_time, 2)
        
        return stats
    
    def process_multiple_files(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Przetwarza wiele plików DXF
        
        Args:
            file_paths: Lista ścieżek do plików DXF
            
        Returns:
            Lista wyników przetwarzania
        """
        results = []
        for file_path in file_paths:
            if file_path.exists() and file_path.suffix.lower() == '.dxf':
                result = self.process_dxf_file(file_path)
                results.append(result)
            else:
                logger.warning(f"Plik nie istnieje lub nie jest plikiem DXF: {file_path}")
        
        return results
    
    def export_to_json(self, output_path: Path) -> None:
        """Eksportuje właściwości do pliku JSON"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.properties, f, ensure_ascii=False, indent=2)
            logger.info(f"Wyeksportowano właściwości do: {output_path}")
        except Exception as e:
            logger.error(f"Błąd eksportu do JSON: {str(e)}")


def process_dxf_directory(directory_path: Path) -> List[Dict[str, Any]]:
    """
    Przetwarza wszystkie pliki DXF w katalogu
    
    Args:
        directory_path: Ścieżka do katalogu z plikami DXF
        
    Returns:
        Lista wyników przetwarzania
    """
    processor = DXFProcessor()
    
    if not directory_path.exists():
        logger.error(f"Katalog nie istnieje: {directory_path}")
        return []
    
    dxf_files = list(directory_path.glob("*.dxf"))
    
    if not dxf_files:
        logger.warning(f"Nie znaleziono plików DXF w katalogu: {directory_path}")
        return []
    
    logger.info(f"Znaleziono {len(dxf_files)} plików DXF")
    
    return processor.process_multiple_files(dxf_files)


if __name__ == "__main__":
    # Test przetwarzania
    from config import DXF_DIR
    
    print("Test przetwarzania plików DXF...")
    results = process_dxf_directory(DXF_DIR)
    
    for result in results:
        print(f"\nPlik: {result['file_name']}")
        if 'error' in result:
            print(f"Błąd: {result['error']}")
        else:
            stats = result['statistics']
            print(f"  Elementów: {stats['total_elements']}")
            print(f"  Całkowita długość: {stats['total_length']:.2f} m")
            print(f"  Całkowita powierzchnia: {stats['total_area']:.2f} m²")
            print(f"  Szacowany czas: {stats['estimated_time_hours']:.2f} h")
