from __future__ import unicode_literals
import re
import json

# ngutil
from ngutil.common import _NGUtilCommon

class _NGUtilIPTables(_NGUtilCommon):
    """
    Class for parsing and updating iptables firewall rules.
    """
    def __init__(self):
        super(_NGUtilIPTables, self).__init__()
        
        # Firewall configuration
        self._config = '/etc/sysconfig/iptables'
    
        # Firewall tables / selected table
        self._tables = {}
        self._table  = None
    
        # Parse existing rules
        self._parse()
    
    def select_table(self, name):
        """
        Select a table to modify chains/rules for.
        """
        if not name in self._tables:
            self.die('Unable to locate table \'{0}\''.format(table))
        self._table = name
    
    def select_chain(self, name):
        """
        Select a chain to modify rules for.
        """
        if not name in self._tables[self._table]:
            self.die('Unable to locate chain \'{0}\' in table \'{1}\''.format(name, self._table))
        self._chain = name
    
    def add_chain(self, name, target='ACCEPT'):
        """
        Add a new firewall chain.
        """
        if not self._table:
            self.die('Cannot add chain \'{0}\', no table selected...'.format(name))
        
        # Check if the chain exists
        if name in self._tables[self._table]:
            self.die('Unable to add chain \'{0}\' to table \'{1}\', already exists'.format(name, self._table))
    
        # Add the chain
        self.run_command('iptables -t {0} -N {1} -j {2}'.format(table, name, target))
        self.feedback.success('Added chain \'{0}\' to table \'{1}\' with target: {2}'.format(name, self._table, target))
    
    def add_rule(self, params):
        """
        Add a rule to a table chain.
        """
        if not self._table:
            self.die('Cannot add iptables rule, no table selected')
        if not self._chain:
            self.die('Cannot add iptables rule, no chain selected')
            
        # Make sure the rule doesn't exist yet
        for rule in self._tables[self._table][self._chain]['rules']:
            if rule.get('--dport', False) and rule['--dport'] == params.get('--dport', None):
                return self.feedback.info('Rule matching --dport {0} already exists, skipping...'.format(params.get('--dport')))
            
        # Define the rule creation command
        proto_cmd = '-p {0} --dport {1}'.format(params.get('-p', 'tcp'), params.get('--dport'))
        state_cmd = '-m state --state {0} -j {1}'.format(params.get('-m state --state', 'NEW'), params.get('-j', 'ACCEPT'))
        rule_cmd  = 'iptables -t {0} -A {1} {2} {3}'.format(self._table, self._chain, proto_cmd, state_cmd)
        
        # Create the rule
        self.run_command(rule_cmd, shell=True)
        self.feedback.success('Added iptables rule: \'{0}\''.format(rule_cmd))
    
        # Reparse the configuration
        self._parse()
    
    def get_table(self, name):
        """
        Retrieve table attributes.
        """
        return self._tables.get('name', None)
    
    def _get_iptables_param(self, param, line):
        """
        Parse out a parameter from an iptables rule line.
        """
        if '{0} '.format(param) in line:
            return re.compile(r'^.*{0}[ ]([^ ]+).*$'.format(param)).sub(r'\g<1>', line).rstrip()
        return None
    
    def _parse(self):
        """
        Parse existing iptables rules.
        """
        
        # Parse existing rules
        code, out, err = self.run_command('iptables-save')
        
        # Current table
        this_table = None
        
        # Parse rules in memory
        for line in out.split('\n'):
            
            # Parse out the current table
            if line.startswith('*'):
                this_table = re.compile(r'^\*(.*$)').sub(r'\g<1>', line).rstrip()
                self._tables[this_table] = {}
                
            # Parse the current chain
            if line.startswith(':'):
                regex = re.compile(r'^:([^ ]+)[ ]+([^ ]+).*$')
                
                # Chain attributes
                chain_name   = regex.sub(r'\g<1>', line).rstrip()
                chain_target = regex.sub(r'\g<2>', line).rstrip()
                
                # Extract chain attributes
                self._tables[this_table][chain_name] = {
                    'target': chain_target,
                    'rules':  []
                }
                
            # Parse the current rule
            if line.startswith('-A'):
                rule_chain  = self._get_iptables_param('-A', line)
                self._tables[this_table][rule_chain]['rules'].append({
                    '--dport': self._get_iptables_param('--dport', line),
                    '--sport': self._get_iptables_param('--sport', line),
                    '--state': self._get_iptables_param('--state', line),
                    '-j': self._get_iptables_param('-j', line),
                    '-p': self._get_iptables_param('-p', line),
                    '-s': self._get_iptables_param('-s', line),
                    '-d': self._get_iptables_param('-d', line)
                })
    
    def save(self, restart=False):
        """
        Save and optionally restart iptables.
        """
        self.run_command('iptables-save > {0}'.format(self._config), shell=True)
        self.feedback.success('Saved iptables rules -> {0}'.format(self._config))
        
        # If restarting
        if restart:
            self.run_command('service iptables restart', shell=True)
            self.feedback.success('Restarted iptables')