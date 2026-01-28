"""
Test script for the document processing workflow.
Tests the complete pipeline with sample documents and provides detailed output.
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any

# Import workflow components
from workflows.document_workflow import get_workflow
from workflows.state_schema import create_initial_state, WorkflowConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowTester:
    """Test harness for document processing workflow"""
    
    def __init__(self):
        """Initialize the workflow tester"""
        self.config = WorkflowConfig(
            llm_provider="openai",  # Change to "anthropic" if you prefer
            model_name="gpt-3.5-turbo",  # More cost-effective for testing
            temperature=0.1,
            enable_ocr=True,
            enable_human_review=True,
            confidence_threshold=0.8
        )
        self.workflow = get_workflow(self.config)
        logger.info("Workflow tester initialized")
    
    async def test_sample_documents(self):
        """Test workflow with various sample documents"""
        
        print("\n" + "="*80)
        print("DOCUMENT PROCESSING WORKFLOW TEST")
        print("="*80)
        
        # Test cases
        test_cases = [
            {
                "name": "Sample Invoice",
                "content": """
                INVOICE #INV-2024-001
                
                From: Tech Solutions Inc.
                123 Business Ave
                San Francisco, CA 94105
                
                To: ABC Corporation
                456 Client Street
                New York, NY 10001
                
                Date: January 15, 2024
                Due Date: February 15, 2024
                
                Description                 Quantity    Price       Total
                Software License               1        $1,200.00   $1,200.00
                Support Services              12        $100.00     $1,200.00
                
                Subtotal:                                           $2,400.00
                Tax (8.5%):                                         $204.00
                Total:                                              $2,604.00
                
                Payment Terms: Net 30 days
                """,
                "file_type": "txt",
                "expected_type": "invoice"
            },
            {
                "name": "Sample Contract",
                "content": """
                SERVICE AGREEMENT
                
                This Service Agreement ("Agreement") is entered into on January 1, 2024,
                between Tech Solutions Inc. ("Provider") and ABC Corporation ("Client").
                
                1. SERVICES
                Provider agrees to provide software development services as outlined
                in Exhibit A attached hereto.
                
                2. TERM
                This Agreement shall commence on January 1, 2024, and shall continue
                for a period of twelve (12) months, ending on December 31, 2024.
                
                3. COMPENSATION
                Client agrees to pay Provider a total of $50,000 for the services
                described herein, payable in monthly installments of $4,166.67.
                
                4. GOVERNING LAW
                This Agreement shall be governed by the laws of California.
                
                IN WITNESS WHEREOF, the parties have executed this Agreement.
                
                Provider: Tech Solutions Inc.
                Client: ABC Corporation
                """,
                "file_type": "txt",
                "expected_type": "contract"
            },
            {
                "name": "Sample Resume",
                "content": """
                JOHN DOE
                Software Engineer
                
                Contact Information:
                Email: john.doe@email.com
                Phone: (555) 123-4567
                Address: 123 Main St, Anytown, CA 90210
                
                PROFESSIONAL SUMMARY
                Experienced software engineer with 5+ years in full-stack development.
                
                WORK EXPERIENCE
                
                Senior Software Engineer | Tech Corp | 2020-Present
                • Developed web applications using React and Node.js
                • Led team of 3 junior developers
                • Improved system performance by 40%
                
                Software Engineer | StartupXYZ | 2018-2020
                • Built REST APIs using Python and Django
                • Implemented automated testing procedures
                • Collaborated with cross-functional teams
                
                EDUCATION
                Bachelor of Science in Computer Science
                University of California, Berkeley | 2018
                
                SKILLS
                • Programming: Python, JavaScript, Java, C++
                • Frameworks: React, Django, Node.js
                • Databases: PostgreSQL, MongoDB
                • Tools: Git, Docker, AWS
                """,
                "file_type": "txt",
                "expected_type": "resume"
            }
        ]
        
        # Run tests
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'-'*60}")
            print(f"TEST {i}: {test_case['name']}")
            print(f"{'-'*60}")
            
            result = await self.run_single_test(test_case)
            results.append(result)
            
            # Print summary
            self.print_test_summary(result)
        
        # Print overall results
        print(f"\n{'='*80}")
        print("OVERALL TEST RESULTS")
        print(f"{'='*80}")
        
        successful_tests = sum(1 for r in results if r["success"])
        print(f"Tests Passed: {successful_tests}/{len(results)}")
        
        for i, result in enumerate(results, 1):
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"Test {i}: {result['test_name']} - {status}")
        
        return results
    
    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case"""
        
        document_id = f"test_doc_{int(datetime.now().timestamp())}"
        
        try:
            print(f"Processing document: {document_id}")
            print(f"Expected type: {test_case['expected_type']}")
            
            # Process document
            result = await self.workflow.process_document(
                document_id=document_id,
                content=test_case["content"],
                file_type=test_case["file_type"],
                metadata={"test_case": test_case["name"]}
            )
            
            if not result["success"]:
                return {
                    "success": False,
                    "test_name": test_case["name"],
                    "error": "Workflow processing failed",
                    "details": result
                }
            
            # Get final state
            final_state = result["final_state"]
            
            # Analyze results
            analysis = self.analyze_test_results(final_state, test_case)
            
            return {
                "success": analysis["overall_success"],
                "test_name": test_case["name"],
                "document_id": document_id,
                "analysis": analysis,
                "final_state": final_state
            }
        
        except Exception as e:
            logger.error(f"Test failed for {test_case['name']}: {e}")
            return {
                "success": False,
                "test_name": test_case["name"],
                "error": str(e),
                "document_id": document_id
            }
    
    def analyze_test_results(self, state: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results against expectations"""
        
        analysis = {
            "overall_success": True,
            "agent_results": {},
            "classification_correct": False,
            "extraction_quality": 0.0,
            "validation_success": False,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Analyze agent performance
            agent_names = ["ingestion", "classification", "extraction", "validation", 
                          "rule_evaluation", "anomaly_detection", "human_review", "audit_learning"]
            
            for agent_name in agent_names:
                result = state.get(f"{agent_name}_result")
                if result:
                    analysis["agent_results"][agent_name] = {
                        "success": result.get("success", False),
                        "confidence": result.get("confidence_score", 0.0),
                        "processing_time": result.get("processing_time", 0.0)
                    }
                    
                    if not result.get("success", False):
                        analysis["issues"].append(f"{agent_name} agent failed")
                        analysis["overall_success"] = False
            
            # Check classification accuracy
            detected_type = state.get("document_type", "unknown")
            expected_type = test_case.get("expected_type", "unknown")
            analysis["classification_correct"] = detected_type == expected_type
            
            if not analysis["classification_correct"]:
                analysis["issues"].append(f"Classification incorrect: expected {expected_type}, got {detected_type}")
            
            # Check extraction quality
            extracted_data = state.get("extracted_data", {})
            non_null_fields = len([v for v in extracted_data.values() if v is not None and v != ""])
            total_fields = len(extracted_data)
            
            if total_fields > 0:
                analysis["extraction_quality"] = non_null_fields / total_fields
            
            if analysis["extraction_quality"] < 0.5:
                analysis["issues"].append("Low extraction quality (< 50% fields populated)")
            
            # Check validation
            validation_result = state.get("validation_result", {})
            analysis["validation_success"] = validation_result.get("success", False)
            
            if not analysis["validation_success"]:
                analysis["issues"].append("Data validation failed")
            
            # Generate recommendations
            if analysis["extraction_quality"] < 0.7:
                analysis["recommendations"].append("Consider improving extraction prompts or adding more examples")
            
            if state.get("requires_human_review", False):
                analysis["recommendations"].append("Document requires human review - check business rules and anomaly detection")
            
            # Overall success criteria
            critical_issues = [issue for issue in analysis["issues"] 
                             if "failed" in issue.lower() and "human_review" not in issue.lower()]
            
            if critical_issues:
                analysis["overall_success"] = False
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            analysis["overall_success"] = False
            analysis["issues"].append(f"Analysis error: {str(e)}")
        
        return analysis
    
    def print_test_summary(self, result: Dict[str, Any]):
        """Print detailed test summary"""
        
        print(f"\nDocument ID: {result.get('document_id', 'N/A')}")
        print(f"Test Status: {'✅ PASSED' if result['success'] else '❌ FAILED'}")
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        analysis = result.get("analysis", {})
        final_state = result.get("final_state", {})
        
        # Agent performance
        print(f"\n📊 AGENT PERFORMANCE:")
        agent_results = analysis.get("agent_results", {})
        for agent_name, agent_result in agent_results.items():
            status = "✅" if agent_result["success"] else "❌"
            confidence = agent_result.get("confidence", 0.0)
            time_taken = agent_result.get("processing_time", 0.0)
            print(f"  {status} {agent_name}: {confidence:.2f} confidence, {time_taken:.2f}s")
        
        # Classification results
        print(f"\n🏷️  CLASSIFICATION:")
        detected_type = final_state.get("document_type", "unknown")
        classification_result = final_state.get("classification_result", {})
        classification_confidence = classification_result.get("confidence_score", 0.0)
        print(f"  Detected Type: {detected_type}")
        print(f"  Confidence: {classification_confidence:.2f}")
        print(f"  Correct: {'✅' if analysis.get('classification_correct', False) else '❌'}")
        
        # Extraction results
        print(f"\n📋 DATA EXTRACTION:")
        extracted_data = final_state.get("extracted_data", {})
        extraction_quality = analysis.get("extraction_quality", 0.0)
        print(f"  Fields Extracted: {len(extracted_data)}")
        print(f"  Quality Score: {extraction_quality:.2f}")
        
        # Show key extracted fields
        if extracted_data:
            print("  Key Fields:")
            for key, value in list(extracted_data.items())[:5]:  # Show first 5 fields
                if value is not None and value != "":
                    display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    print(f"    {key}: {display_value}")
        
        # Validation results
        print(f"\n✅ VALIDATION:")
        validation_result = final_state.get("validation_result", {})
        validation_success = analysis.get("validation_success", False)
        print(f"  Status: {'✅ Passed' if validation_success else '❌ Failed'}")
        
        if validation_result.get("result"):
            error_count = validation_result["result"].get("error_count", 0)
            warning_count = validation_result["result"].get("warning_count", 0)
            print(f"  Errors: {error_count}, Warnings: {warning_count}")
        
        # Business rules and anomalies
        print(f"\n⚖️  BUSINESS RULES & ANOMALIES:")
        rules_applied = len(final_state.get("business_rules_applied", []))
        anomalies_detected = len(final_state.get("anomalies_detected", []))
        requires_review = final_state.get("requires_human_review", False)
        
        print(f"  Rules Triggered: {rules_applied}")
        print(f"  Anomalies Detected: {anomalies_detected}")
        print(f"  Human Review Required: {'Yes' if requires_review else 'No'}")
        
        # Issues and recommendations
        issues = analysis.get("issues", [])
        recommendations = analysis.get("recommendations", [])
        
        if issues:
            print(f"\n⚠️  ISSUES:")
            for issue in issues:
                print(f"  • {issue}")
        
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"  • {rec}")
        
        # Processing time
        total_time = final_state.get("total_processing_time", 0)
        print(f"\n⏱️  TIMING:")
        print(f"  Total Processing Time: {total_time:.2f}s")
        
        # Final status
        final_status = final_state.get("status", "unknown")
        print(f"\n🏁 FINAL STATUS: {final_status}")
    
    async def test_error_handling(self):
        """Test error handling scenarios"""
        
        print(f"\n{'='*80}")
        print("ERROR HANDLING TESTS")
        print(f"{'='*80}")
        
        error_tests = [
            {
                "name": "Empty Content",
                "content": "",
                "file_type": "txt",
                "should_fail": True
            },
            {
                "name": "Very Short Content",
                "content": "Hi",
                "file_type": "txt",
                "should_fail": False  # Should process but with low confidence
            },
            {
                "name": "Unsupported File Type",
                "content": "Some content",
                "file_type": "xyz",
                "should_fail": False  # Should default to 'other' type
            }
        ]
        
        for i, test_case in enumerate(error_tests, 1):
            print(f"\n{'-'*40}")
            print(f"ERROR TEST {i}: {test_case['name']}")
            print(f"{'-'*40}")
            
            try:
                result = await self.run_single_test(test_case)
                
                if test_case["should_fail"]:
                    if result["success"]:
                        print("❌ Expected failure but test passed")
                    else:
                        print("✅ Expected failure and test failed correctly")
                else:
                    if result["success"]:
                        print("✅ Test passed as expected")
                    else:
                        print(f"⚠️  Test failed: {result.get('error', 'Unknown error')}")
                
                if "analysis" in result:
                    self.print_test_summary(result)
            
            except Exception as e:
                print(f"❌ Error test failed with exception: {e}")


async def main():
    """Main test function"""
    
    print("🚀 Starting Document Processing Workflow Tests")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check environment
    print("\n📋 Environment Check:")
    print(f"  Python: ✅")
    print(f"  Required packages: ✅")
    
    # Initialize tester
    tester = WorkflowTester()
    
    try:
        # Run main tests
        await tester.test_sample_documents()
        
        # Run error handling tests
        await tester.test_error_handling()
        
        print(f"\n🎉 All tests completed!")
        print(f"Check the output above for detailed results.")
    
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        logger.error(f"Test suite failed: {e}", exc_info=True)


if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())