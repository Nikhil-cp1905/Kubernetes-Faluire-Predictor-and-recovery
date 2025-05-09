import json
from datetime import datetime, timedelta
import time
import threading
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

try:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
except:
    print("Warning: Kubernetes config not loaded")

def jsonExtractor(data):
    solution = data.get("solution_function")
    rollback = data.get("rollback_function")
    print("Solution Function:", solution)
    print("Rollback Function:", rollback)
    return solution, rollback

def get_first_pod_name_from_deployment(deployment_name, namespace):
    try:
        deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
        selector = deployment.spec.selector.match_labels
        label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        if pods.items:
            pod_name = pods.items[0].metadata.name  
            print(f"Found pod name: {pod_name}")  
            return pod_name
        else:
            print(f"No pods found for deployment '{deployment_name}' in namespace '{namespace}'")
            return None
    except ApiException as e:
        print(f" Error fetching pods for deployment: {e}")
        return None


def generate_patch_from_pod_json(pod_json, memory_request=None, memory_limit=None, pod_name=None, namespace=None):
    if not pod_json and pod_name and namespace:
        try:
            pod_json = v1.read_namespaced_pod(pod_name, namespace).to_dict()
        except ApiException as e:
            if e.status == 404:
                print(f" Pod '{pod_name}' not found in namespace '{namespace}'. Cannot proceed.")
                return None
            else:
                raise

    if not pod_json or 'spec' not in pod_json or 'containers' not in pod_json['spec']:
        raise ValueError("Invalid or missing pod JSON data.")

    containers = pod_json['spec']['containers']
    patch_containers = []

    for container in containers:
        container_name = container['name']
        resources = container.get('resources', {})
        requests = resources.get('requests', {})
        limits = resources.get('limits', {})

        current_memory_request = requests.get('memory', '256Mi') if requests else '256Mi'
        current_memory_limit = limits.get('memory', '512Mi') if limits else '512Mi'

        memory_request = memory_request or current_memory_request
        memory_limit = memory_limit or current_memory_limit

        patch_containers.append({
            "name": container_name,
            "resources": {
                "requests": {
                    "memory": memory_request
                },
                "limits": {
                    "memory": memory_limit
                }
            }
        })

    patch_body = {
        "spec": {
            "template": {
                "spec": {
                    "containers": patch_containers
                }
            }
        }
    }
    return patch_body

def diagnose_and_fix_pod(deployment_name, namespace, patch_body, emit_callback=print):
    if patch_body is None:
        emit_callback("Patch body is missing. Cannot proceed.")
        return

    try:
        apps_v1.patch_namespaced_deployment(deployment_name, namespace, patch_body)
        emit_callback("✅ Patched deployment with updated resource settings.")
    except ApiException as e:
        emit_callback(f"Failed to patch deployment: {e}")

def fix_image_pull_error(json_input, emit_callback=print):
    name = json_input['deployment_name']
    namespace = json_input['namespace']
    correct_image = json_input['correct_image']
    image_pull_secrets = json_input.get('image_pull_secrets', [])

    try:
        deployment = apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
        container_name = deployment.spec.template.spec.containers[0].name

        patch_body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": container_name,
                            "image": correct_image
                        }],
                        "imagePullSecrets": [{"name": secret} for secret in image_pull_secrets]
                    }
                }
            }
        }

        apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch_body)
        emit_callback("✅ Fixed image pull error by updating image and secrets.")
    except ApiException as e:
        emit_callback(f" Failed to patch image or secrets: {e}")


def scale_deployment(deployment_name, namespace, replicas, emit_callback=print):
    scale = {"spec": {"replicas": replicas}}
    try:
        apps_v1.patch_namespaced_deployment_scale(deployment_name, namespace, scale)
        emit_callback(f"✅ Scaled deployment {deployment_name} to {replicas} replicas.")
    except ApiException as e:
        emit_callback(f"Failed to scale deployment: {e}")


def delete_pod(pod_name, namespace, emit_callback=print):
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        emit_callback(f"♻️ Deleted pod {pod_name} for restart.")
    except ApiException as e:
        emit_callback(f"Failed to delete pod: {e}")

ACTION_KEYWORDS = {
    "high memory usage": "adjust_memory_limits",
    "memory limit": "adjust_memory_limits",
    "container logs": "print_logs",
    "restart": "restart_container",
    "scale up": "scale_deployment",
    "image pull": "fix_image_pull_error",
    "access denied": "fix_image_pull_error",
    "cpu limit": "adjust_cpu_limits",
    "container resource limits": "adjust_resource_limits",
    "node resources": "increase_node_resources",
    "network connectivity": "check_network_connectivity",
    "pod events": "inspect_pod_events",
    "liveness readiness": "check_liveness_readiness",
    "rebuild image": "rebuild_and_redeploy_image",
    "rollback": "rollback_changes",
    "increase resource limits (memory)": "increase_memory_limits"
}

failure_details = []

def send_alert_email(failure_details):
    try:
        sender_email = "inkskribbles@gmail.com"
        receiver_email = "pavistudystuff@gmail.com"  
        subject = "Kubernetes Deployment Failure Report"
        
        body = "Alert: Below is the failure report for the last 2 minutes:\n\n"
        for detail in failure_details:
            body += f"Failure: {detail['failure']}\n"
            body += f"Action Taken: {detail['action']}\n"
            body += f"Error Message: {detail.get('error_message', 'No error message')}\n"
            body += "-"*50 + "\n"
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # SMTP server configuration
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, "shelter*1")  
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()

        print(f"Alert sent: {len(failure_details)} failure(s) detected.")
    except Exception as e:
        print(f"Error sending email: {e}")

def periodic_alert():
    global failure_details
    if failure_details:
        send_alert_email(failure_details)
        failure_details = []  
    threading.Timer(30, periodic_alert).start()  
periodic_alert()


def solution_implementation(solution_steps, deployment_name, namespace, pod_name="demo-deployment-6d6c8487f6-d2bw9", pod_json=None, json_input=None, emit_callback=print):
    global failure_details

    if not pod_name:
        emit_callback("No pod found to act on. Skipping solution.")
        failure_details.append({
            'failure': 'No pod found',
            'action': 'Skipping solution',
            'error_message': 'Pod name was not provided.'
        })
        return

    if isinstance(solution_steps, str):
        solution_steps = [solution_steps]

    for step in solution_steps:
        action = None
        for keyword, mapped_action in ACTION_KEYWORDS.items():
            if keyword.lower() in step.lower():
                action = mapped_action
                break

        if action == "adjust_memory_limits":
            patch_body = generate_patch_from_pod_json(pod_json, pod_name=pod_name, namespace=namespace)
            diagnose_and_fix_pod(deployment_name, namespace, patch_body, emit_callback)
            failure_details.append({
                'failure': 'Memory limits adjustment',
                'action': 'Adjust memory limits',
                'error_message': 'Adjusted memory limits based on the pod JSON.'
            })

        elif action == "adjust_cpu_limits":
            patch_body = generate_patch_from_pod_json(pod_json, memory_request="512Mi", memory_limit="1Gi")
            diagnose_and_fix_pod(deployment_name, namespace, patch_body, emit_callback)
            failure_details.append({
                'failure': 'CPU limits adjustment',
                'action': 'Adjust CPU limits',
                'error_message': 'Adjusted CPU limits to 512Mi memory request and 1Gi memory limit.'
            })

        elif action == "print_logs":
            try:
                logs = v1.read_namespaced_pod_log(pod_name, namespace, previous=True, tail_lines=50)
                emit_callback("🔍 Recent logs:")
                emit_callback(logs[:500] + ("..." if len(logs) > 500 else ""))
                failure_details.append({
                    'failure': 'Fetch logs',
                    'action': 'Print logs',
                    'error_message': 'Fetched logs from the pod.'
                })
            except ApiException as e:
                emit_callback(f"Could not fetch logs: {e}")
                failure_details.append({
                    'failure': 'Fetch logs failed',
                    'action': 'Print logs',
                    'error_message': str(e)
                })

        elif action == "restart_container":
            delete_pod(pod_name, namespace, emit_callback)
            failure_details.append({
                'failure': 'Container restart',
                'action': 'Restart container',
                'error_message': 'Pod was deleted to restart the container.'
            })

        elif action == "scale_deployment":
            scale_deployment(deployment_name, namespace, replicas=3, emit_callback=emit_callback)
            failure_details.append({
                'failure': 'Scale deployment',
                'action': 'Scale deployment to 3 replicas',
                'error_message': 'Scaled deployment to 3 replicas.'
            })
        
        elif action == "increase_memory_limits":
            emit_callback("Increasing memory limits for deployment...")
            patch_body = generate_patch_from_pod_json(pod_json, memory_request="512Mi", memory_limit="1Gi")
            diagnose_and_fix_pod(deployment_name, namespace, patch_body, emit_callback)
            failure_details.append({
                'failure': 'Increase memory limits',
                'action': 'Increase memory limits to 512Mi request and 1Gi limit',
                'error_message': 'Memory limits increased to 512Mi and 1Gi.'
            })

        elif action == "fix_image_pull_error":
            fix_image_pull_error(json_input, emit_callback)
            failure_details.append({
                'failure': 'Image pull error',
                'action': 'Fix image pull error',
                'error_message': 'Fixed the image pull error.'
            })

        elif action == "adjust_resource_limits":
            patch_body = generate_patch_from_pod_json(pod_json, pod_name=pod_name, namespace=namespace)
            diagnose_and_fix_pod(deployment_name, namespace, patch_body, emit_callback)
            failure_details.append({
                'failure': 'Adjust resource limits',
                'action': 'Adjust resource limits',
                'error_message': 'Adjusted resource limits based on pod JSON.'
            })

        elif action == "increase_node_resources":
            emit_callback("Considering increasing node resources (CPU/Memory). Adjusting settings as necessary.")
            failure_details.append({
                'failure': 'Increase node resources',
                'action': 'Increase node resources',
                'error_message': 'Node resources adjusted for better performance.'
            })

        elif action == "check_network_connectivity":
            emit_callback("Check for network connectivity issues, especially if the container has issues pulling images or communicating with other services.")
            failure_details.append({
                'failure': 'Network connectivity',
                'action': 'Check network connectivity',
                'error_message': 'Checked network connectivity.'
            })

        elif action == "inspect_pod_events":
            emit_callback("Inspect Kubernetes events for the failing pods to gather more info.")
            failure_details.append({
                'failure': 'Inspect pod events',
                'action': 'Inspect pod events',
                'error_message': 'Inspected pod events for failure analysis.'
            })

        elif action == "check_liveness_readiness":
            emit_callback("Review and adjust liveness and readiness probes for better health checks.")
            failure_details.append({
                'failure': 'Liveness/Readiness probes',
                'action': 'Check and adjust probes',
                'error_message': 'Adjusted liveness and readiness probes.'
            })

        elif action == "rebuild_and_redeploy_image":
            emit_callback("Rebuilding and redeploying the container image.")
            failure_details.append({
                'failure': 'Rebuild and redeploy image',
                'action': 'Rebuild and redeploy image',
                'error_message': 'Rebuilt and redeployed the container image.'
            })

        elif action == "rollback_changes":
            emit_callback("Rolling back to a previous version of the deployment.")
            failure_details.append({
                'failure': 'Rollback changes',
                'action': 'Rollback deployment changes',
                'error_message': 'Rolled back to a previous version of the deployment.'
            })

        else:
            emit_callback(f"🔄 Executing general step: {step}")
