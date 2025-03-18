1. Docker Desktopをインストール
https://docs.docker.jp/desktop/install/mac-install.html
→ githubと連携


2. Docker Build
※ Docker Desktopを入れておく
https://www.docker.com/ja-jp/products/docker-desktop/
--------
% brew install docker
% docker build --platform linux/amd64 -t discover-stocks-test:v1 .
--------


3. Azure セットアップ
https://learn.microsoft.com/ja-jp/azure/aks/learn/quick-kubernetes-deploy-portal?tabs=azure-cli
→ とりあえず無料プランでK8Sサービスを申し込み


4. Azure CLIの準備
--------
$ brew update
$ brew install azure-cli
$ az --version
$ az login
$ az account show
----
% az account show
{
  "environmentName": "AzureCloud",
...
  "user": {
    "name": "xxx",
    "type": "user"
  }
}
----
--------


5. Azure Conteiner Repositry作成
→ ContainerイメージをRegistryへあげるために作る。
https://qiita.com/kk-ishii/items/720d26467484684fd31d
→ Container Registryを作成する

例:
レジストリ名 discoverstockstest


6. Azure ACRへプッシュ
(1) Azure, ACRへログイン
% az login
→ 「[1] *  Azure subscription 1  ... 既定のディレクトリ」を選ぶ
% az acr login --name discoverstockstest
→ 「Login Succeeded」が表示され、DockerRegistryへログインできていること。

(2) Registryの確認
% az acr list --query "[].{Name:name}" --output table
→ DockerRegistryが表示されること.
---------------------
Name
------------------
discoverstockstest
---------------------

(3) Pushする
----
% docker tag discover-stocks-test:v1 discoverstockstest.azurecr.io/discover-stocks-test:v1
% docker push discoverstockstest.azurecr.io/discover-stocks-test:v1
----

以下のようにpush成功する事
----
% docker push discoverstockstest.azurecr.io/discover-stocks-test:v1
The push refers to repository [discoverstockstest.azurecr.io/discover-stocks-test]
091eb8249475: Pushed 
0acf70933f59: Pushed 
6e02a90e58ae: Pushed 
7355ffe791e5: Pushed 
ec97aceb5f17: Pushed 
a640f05270f0: Pushed 
daaced89b65b: Pushed 
353e14e5cc47: Pushed 
f299e0671245: Pushed 
7cd785773db4: Pushed 
f6d72b00ae7c: Pushed 
255774e0027b: Pushed 
v1: digest: sha256:909fd9918af82411138c584b36333376136216d97d95ed3f7ae1c1a841fec7ff size: 856
ogalush@MacBook-Pro1 discover-stocks_feature-k8sPlusPersistentVolumes202503 % 
----
→ ソースの準備はひとまずOK.


7. Kubernetes サービス
(1) Node作成
Podを載せるNodeを準備する。
→ 「作成」→「Kubernetesクラスタの作成」
----
サブスクリプション Azure subscription 1
リソース グループ discover-stocks-test_group
リージョン Japan West
Kubernetes クラスター名 discover-stocks-test
Kubernetes バージョン 1.30.9
自動アップグレード patch
自動アップグレード スケジューラ 毎週日曜日 (おすすめ)
ノード セキュリティ チャネルの種類 NodeImage
セキュリティ チャネル スケジューラ 毎週日曜日 (おすすめ)
ノード プール ノード プール 1
仮想ノードを有効にする 無効
アクセス
リソース ID System-assigned managed identity
ローカル アカウント 有効
認証と認可 Kubernetes RBAC を使用したローカル アカウント
暗号化の種類 (既定) プラットフォーム マネージド キーを使用した保存時の暗号化
ネットワーク プライベート クラスター 無効
認可された IP 範囲 無効
ネットワーク構成 Azure CNI オーバーレイ
DNS 名のプレフィックス discover-stocks-test-dns
ネットワーク ポリシー なし
ロード バランサー Standard
統合 コンテナー レジストリ
なし
サービス メッシュ 無効
Azure Policy 無効
監視中
コンテナー ログを有効にする 無効
Prometheus メトリックを有効にする 無効
Grafana を有効にする 無効
アラート ルール 2 個のルール
詳細
インフラストラクチャ リソース グループ
MC_discover-stocks-test_group_discover-stocks-test_japanwest

セキュリティ Microsoft Defender for Cloud
Free OpenID Connect (OIDC) 有効
ワークロード ID 有効
イメージ クリーナー 有効
タグ なし
----


8. デプロイ
(1) k8sへログイン
----
% az aks get-credentials --resource-group discover-stocks-test_group --name discover-stocks-test
Merged "discover-stocks-test" as current context in /Users/ogalush/.kube/config

% kubectl cluster-info
% kubectl config current-context
discover-stocks-test
----
→ Azure k8sで作成したクラスタ名が出力されればOK.


(2) Node確認
→ Containerを稼働させる箱が表示されればOK.
----
% kubectl get nodes
NAME                                STATUS   ROLES    AGE   VERSION
aks-agentpool-32700588-vmss000000   Ready    <none>   10m   v1.30.9
aks-agentpool-32700588-vmss000001   Ready    <none>   10m   v1.30.9
----
→ Readyで何台か表示されればOK.


(3) Pod確認
% kubectl get pods --all-namespaces
→ AzureのPodが表示されればOK.
----
NAMESPACE     NAME                                                   READY   STATUS    RESTARTS   AGE
kube-system   azure-cns-pxqlk                                        1/1     Running   0          11m
kube-system   azure-cns-qbn5c                                        1/1     Running   0          10m
...(略)...
----

(3) NameSpace作成
→ Deployする先を準備する
----
% kubectl create namespace discover-stocks-test
namespace/discover-stocks-test created

% kubectl get namespaces |grep discover
discover-stocks-test   Active   30s
→ 表示されればOK.
----

(4) podデプロイ
----
% kubectl config set-context --current --namespace=discover-stocks-test

% kubectl apply -f azure-k8s/streamlit-deployment.yaml
deployment.apps/streamlit-app created
service/streamlit-service created
persistentvolumeclaim/streamlit-pvc created

% kubectl apply -f azure-k8s/streamlit-config.yaml
configmap/streamlit-config created

% kubectl rollout restart deployment streamlit-app
deployment.apps/streamlit-app restarted
----

(5) Deploy確認
・Service
----
% kubectl get services
NAME                TYPE           CLUSTER-IP    EXTERNAL-IP      PORT(S)        AGE
streamlit-service   LoadBalancer   10.0.10.190   104.215.26.119   80:31964/TCP   2m45s
----

・Pod
----
% kubectl get pods
NAME                             READY   STATUS    RESTARTS   AGE
streamlit-app-6794c6f564-gwlfx   0/1     Pending   0          26s
streamlit-app-855757d6b5-ct2qb   0/1     Pending   0          5m8s
streamlit-app-855757d6b5-ndkq6   0/1     Pending   0          5m8s
streamlit-app-855757d6b5-wh8hn   0/1     Pending   0          5m8s
----
→ PendingになっているためNG


・Persistent Volume
----
% kubectl get pvc
No resources found in default namespace.
ogalush@MacBook-Pro1 ~ % kubectl get pvc -n discover-stocks-test 
NAME            STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS    VOLUMEATTRIBUTESCLASS   AGE
streamlit-pvc   Pending                                      azurefile-csi   <unset>                 6m43s
----


・Azure Container RegistryへSecret登録する。
プル シークレットを使用して Azure コンテナー レジストリから Kubernetes クラスターにイメージをプルする
https://learn.microsoft.com/ja-jp/azure/container-registry/container-registry-auth-kubernetes
----
service-principal-ID 	レジストリにアクセスするために Kubernetes によって使用されるサービス プリンシパルの ID
service-principal-password 	サービス プリンシパルのパスワード
----
↓
サービス プリンシパルによる Azure Container Registry 認証
https://learn.microsoft.com/ja-jp/azure/container-registry/container-registry-auth-service-principal

簡単そうな以下のページから
https://qiita.com/kenakamu/items/fb8adae1c5ddb906e0f2
----
% az ad sp create-for-rbac --skip-assignment

Option '--skip-assignment' has been deprecated and will be removed in a future release.
The output includes credentials that you must protect. Be sure that you do not include these credentials in your code or check the credentials into your source control. For more information, see https://aka.ms/azadsp-cli
{
  "appId": "de27e76f-xxxxx-xxxx-xxxxx",
  "displayName": "azure-cli-2025-03-18-17-55-24",
  "password": "hogehoge....fooo",
  "tenant": "7205684f-....."
}

% az acr show --resource-group discover-stocks-test_group --name discoverstockstest --query "id" --output tsv
/subscriptions/b44ecb71-..../...../discoverstockstest

% az role assignment create --assignee de27e76f-f337-4110-8b73-d17581901ef1 --scope /subscriptions/b44ecb71-587d-4a9b-9347-7be6508803b5/resourceGroups/discover-stocks-test_group/providers/Microsoft.ContainerRegistry/registries/discoverstockstest --role acrpull
{
  "condition": null,
  "conditionVersion": null,
  "createdBy": null,
  "createdOn": "2025-03-18T17:59:15.125150+00:00",
...(略)...
  "type": "Microsoft.Authorization/roleAssignments",
  "updatedBy": "71ac71ea-9d60-4487-ae4b-c3ff75a15ad5",
  "updatedOn": "2025-03-18T17:59:15.257149+00:00"
}
% 
----


・DockerImageをダウンロードするSecretを準備する
----
% kubectl create secret docker-registry acr-secret \
--docker-server=discoverstockstest.azurecr.io \
--docker-username="de2..." \
--docker-password="..." \
--docker-email=...
secret/acr-secret created


% kubectl get secret acr-secret --output=yaml
→ 内容が表示されればOK.
----

・再確認
----
% kubectl get pods
NAME                             READY   STATUS    RESTARTS   AGE
streamlit-app-697b94d955-4q479   1/1     Running   0          32s
streamlit-app-697b94d955-57wxm   1/1     Running   0          60s
streamlit-app-697b94d955-jlvz2   1/1     Running   0          33s
----
→ 「RUNNING」になればOK.


・表示確認
http://IPアドレス/
→ 表示されればOK.


・Podのエラー詳細を見る場合
% kubectl get pods
% kubectl describe pod streamlit-app-5587b55cdb-dq26f -n discover-stocks-test
→ エラーメッセージを読む

・再反映は以下
% kubectl rollout restart deployment streamlit-app -n discover-stocks-test
