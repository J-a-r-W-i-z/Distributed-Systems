for i in {2..6}; do
    sed -i "s/N=.*/N=$i/g" docker-compose.yml

    make build
    make run &
    sleep 5
    python3 Analysis/A2/A2.py $i
    make stop
    make clean
    sleep 5
done

# sed -i "s/N=.*/N=3/g" docker-compose.yml

# python3 Analysis/A2/plotter.py 2 6
