"""
Descriptor analyzer - extracts and manages descriptors from chat logs.
Builds up a growing list of LLM emotions and user message types over time.
"""
import re
import json
import os
from typing import Set, Dict, List
from collections import defaultdict


class DescriptorAnalyzer:
    """Analyzes chat logs to extract and manage descriptors"""
    
    def __init__(self, log_file: str = "lexi_chat_logs.txt", descriptor_file: str = "lexi_descriptors.json"):
        self.log_file = log_file
        self.descriptor_file = descriptor_file
        self.llm_descriptors: Set[str] = set()
        self.user_descriptors: Set[str] = set()
        self.descriptor_counts: Dict[str, Dict[str, int]] = {
            'llm': defaultdict(int),
            'user': defaultdict(int)
        }
        
        # Load existing descriptors if file exists
        self._load_descriptors()
    
    def _load_descriptors(self):
        """Load descriptors from saved file"""
        if os.path.exists(self.descriptor_file):
            try:
                with open(self.descriptor_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.llm_descriptors = set(data.get('llm_descriptors', []))
                    self.user_descriptors = set(data.get('user_descriptors', []))
                    self.descriptor_counts['llm'] = defaultdict(int, data.get('llm_counts', {}))
                    self.descriptor_counts['user'] = defaultdict(int, data.get('user_counts', {}))
                print(f"Loaded {len(self.llm_descriptors)} LLM descriptors and {len(self.user_descriptors)} user descriptors")
            except Exception as e:
                print(f"Error loading descriptors: {e}")
    
    def _save_descriptors(self):
        """Save descriptors to file with counts"""
        try:
            # Sort descriptors by count (most common first) for better readability
            llm_sorted = sorted(self.descriptor_counts['llm'].items(), key=lambda x: x[1], reverse=True)
            user_sorted = sorted(self.descriptor_counts['user'].items(), key=lambda x: x[1], reverse=True)
            
            data = {
                'llm_descriptors': sorted(list(self.llm_descriptors)),
                'user_descriptors': sorted(list(self.user_descriptors)),
                'llm_counts': dict(self.descriptor_counts['llm']),
                'user_counts': dict(self.descriptor_counts['user']),
                'llm_by_frequency': [{'descriptor': desc, 'count': count} for desc, count in llm_sorted],
                'user_by_frequency': [{'descriptor': desc, 'count': count} for desc, count in user_sorted],
                'total_llm_uses': sum(self.descriptor_counts['llm'].values()),
                'total_user_uses': sum(self.descriptor_counts['user'].values())
            }
            with open(self.descriptor_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving descriptors: {e}")
    
    def parse_log_file(self):
        """Parse the log file and extract all descriptors"""
        if not os.path.exists(self.log_file):
            print(f"Log file {self.log_file} not found")
            return
        
        # Pattern to match descriptors in parentheses
        # Matches: AI: message (emotion) or User: message (descriptor)
        pattern = r'(?:AI:|User:)\s+.*?\s+\(([^)]+)\)'
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all descriptors in parentheses
            matches = re.findall(pattern, content)
            
            # Also check for lines that might have descriptors
            lines = content.split('\n')
            for line in lines:
                # Check for AI: lines with descriptors
                if 'AI:' in line and '(' in line and ')' in line:
                    match = re.search(r'AI:\s+.*?\s+\(([^)]+)\)', line)
                    if match:
                        descriptor = match.group(1).strip().lower()
                        self.llm_descriptors.add(descriptor)
                        self.descriptor_counts['llm'][descriptor] += 1
                
                # Check for User: lines with descriptors
                if 'User:' in line and '(' in line and ')' in line:
                    match = re.search(r'User:\s+.*?\s+\(([^)]+)\)', line)
                    if match:
                        descriptor = match.group(1).strip().lower()
                        self.user_descriptors.add(descriptor)
                        self.descriptor_counts['user'][descriptor] += 1
            
            # Save updated descriptors
            self._save_descriptors()
            
            print(f"Parsed log file: Found {len(self.llm_descriptors)} unique LLM descriptors, {len(self.user_descriptors)} unique user descriptors")
            
        except Exception as e:
            print(f"Error parsing log file: {e}")
    
    def add_descriptor(self, descriptor: str, descriptor_type: str):
        """Add a new descriptor (llm or user)"""
        descriptor = descriptor.strip().lower()
        if descriptor_type == 'llm':
            self.llm_descriptors.add(descriptor)
            self.descriptor_counts['llm'][descriptor] += 1
        elif descriptor_type == 'user':
            self.user_descriptors.add(descriptor)
            self.descriptor_counts['user'][descriptor] += 1
        self._save_descriptors()
    
    def get_all_descriptors(self) -> Dict[str, List[str]]:
        """Get all descriptors sorted by frequency"""
        return {
            'llm': sorted(self.llm_descriptors, key=lambda x: self.descriptor_counts['llm'][x], reverse=True),
            'user': sorted(self.user_descriptors, key=lambda x: self.descriptor_counts['user'][x], reverse=True)
        }
    
    def get_descriptor_stats(self) -> Dict:
        """Get statistics about descriptors"""
        return {
            'total_llm_descriptors': len(self.llm_descriptors),
            'total_user_descriptors': len(self.user_descriptors),
            'most_common_llm': sorted(self.descriptor_counts['llm'].items(), key=lambda x: x[1], reverse=True)[:10],
            'most_common_user': sorted(self.descriptor_counts['user'].items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def print_stats(self):
        """Print descriptor statistics"""
        stats = self.get_descriptor_stats()
        print("\n=== DESCRIPTOR STATISTICS ===")
        print(f"Total LLM descriptors: {stats['total_llm_descriptors']}")
        print(f"Total User descriptors: {stats['total_user_descriptors']}")
        print("\nMost common LLM descriptors:")
        for desc, count in stats['most_common_llm']:
            print(f"  {desc}: {count}")
        print("\nMost common User descriptors:")
        for desc, count in stats['most_common_user']:
            print(f"  {desc}: {count}")
        print("=" * 30)


if __name__ == '__main__':
    # Standalone script to parse log file
    analyzer = DescriptorAnalyzer()
    analyzer.parse_log_file()
    analyzer.print_stats()

