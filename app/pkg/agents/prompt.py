def get_prompt():
    task = f"""
      Use the MCP tool to perform a security audit analysis on Move smart contracts in directory, generating a Markdown format report.

      Objective

      Identify security vulnerabilities, design flaws, and potential risks
      Generate a structured, readable audit report
      Audit Process

      File Browsing - FileSurfer scans all .move files in the directory
      Code Reading - AuditAssistant reads file contents using the MCP tool
      Code Audit - AuditAssistant analyzes code, focusing on:
      Resource safety (leaks, unauthorized access)
      Access control (permission management, privilege escalation)
      Arithmetic issues (overflow, division by zero, precision)
      Logical design flaws
      Object management (ownership, lifecycle)
      Token handling operations
      Reentrancy attack risks
      Report Formatting - OutputAgent organizes and formats the final report
      Report Structure

      1. Executive Summary
      Objectives, scope, and methodology
      2. Identified Issues
      Title, severity (Critical/High/Medium/Low)
      Description, location, problematic code, and specific remediation suggestions
      3. Technical Analysis
      Key component analysis and code quality recommendations
      4. Security Recommendations
      Remediation steps and best practices
      5. Conclusion
      Summary of assessment and risk prioritization
      Quality Requirements

      Clear technical language, specific recommendations
      Include code snippets, ensure traceability
      Prioritize critical security issues
      Agent Collaboration

      FileSurfer: File system scanning
      AuditAssistant: Code reading, auditing, and optimization
      OutputAgent: Report formatting and beautification
    """
    return task